"""本地转写实现：基于 faster-whisper 的 LocalWhisperTranscriber。"""

from __future__ import annotations

from .base import Segment, Transcriber


class LocalWhisperTranscriber(Transcriber):
    """用本地 faster-whisper 模型把音频转写为 Segment 列表。

    重依赖 faster_whisper 仅在真正加载模型时才导入，
    未安装时本模块仍可正常被导入。模型采用延迟加载：
    首次调用 transcribe 时才实例化并缓存到 self._model。
    """

    def __init__(
        self,
        model: str = "base",
        device: str = "auto",
        compute_type: str = "default",
    ) -> None:
        """初始化转写器（不在此处加载模型）。

        Args:
            model: faster-whisper 模型名（如 tiny / base / small / large-v3）。
            device: 运行设备，auto / cpu / cuda。auto 时优先尝试 cuda 并在失败时回退 cpu。
            compute_type: 计算精度，default / int8 / float16 等。
        """
        self._model_name = model
        self._device = device
        self._compute_type = compute_type
        self._model: object | None = None
        self._effective_device: str | None = None

    def _build_model(self, device: str) -> object:
        """构造指定设备上的 WhisperModel（延迟导入 faster_whisper）。"""
        from faster_whisper import WhisperModel

        return WhisperModel(
            self._model_name, device=device, compute_type=self._compute_type
        )

    def _load_model(self) -> object:
        """延迟加载并缓存 WhisperModel 实例。

        device="auto" 时先按 cuda 试探构造，构造即失败则回退 cpu；但真正的 CUDA
        可用性（cuBLAS/cuDNN 等运行库）只有推理时才暴露，由 transcribe() 兜底回退。
        """
        if self._model is not None:
            return self._model

        target = "cuda" if self._device == "auto" else self._device
        try:
            self._model = self._build_model(target)
            self._effective_device = target
        except Exception:  # noqa: BLE001 - 构造失败（缺库/不兼容）即回退 cpu
            self._model = self._build_model("cpu")
            self._effective_device = "cpu"
        return self._model

    @staticmethod
    def _is_device_error(exc: Exception) -> bool:
        """判断异常是否为 GPU/CUDA 运行库相关（用于决定是否回退 CPU）。"""
        msg = str(exc).lower()
        return any(k in msg for k in ("cuda", "cublas", "cudnn", "gpu"))

    def _collect(self, whisper_segments) -> list[Segment]:  # noqa: ANN001
        """把 faster-whisper 的片段（生成器）物化为 Segment 列表。"""
        results: list[Segment] = []
        for seg in whisper_segments:
            results.append(
                Segment(
                    text=seg.text.strip(),
                    start_ms=int(round(seg.start * 1000)),
                    end_ms=int(round(seg.end * 1000)),
                    speaker_label=None,
                )
            )
        return results

    def transcribe(self, audio_path: str) -> list[Segment]:
        """把指定路径的音频文件转写为转写片段列表。

        若在非 CPU 设备上推理时遇到 CUDA 运行库缺失等错误，自动回退到 CPU 重试一次。

        Args:
            audio_path: 音频文件路径。

        Returns:
            按时间排序的 Segment 列表；speaker_label 一律为 None。
        """
        model = self._load_model()
        try:
            whisper_segments, _info = model.transcribe(audio_path)
            return self._collect(whisper_segments)
        except Exception as exc:  # noqa: BLE001
            if self._effective_device != "cpu" and self._is_device_error(exc):
                print(
                    f"[提示] {self._effective_device} 推理失败（{exc}），自动回退到 CPU 重试。",
                    flush=True,
                )
                self._model = self._build_model("cpu")
                self._effective_device = "cpu"
                whisper_segments, _info = self._model.transcribe(audio_path)
                return self._collect(whisper_segments)
            raise
