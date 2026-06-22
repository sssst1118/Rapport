"""麦克风录音：固定时长录制与手动开关录制。

依赖 sounddevice（采集）与 soundfile（写 WAV），两者均延迟导入，
未安装时本模块仍可导入，纯逻辑测试不受影响。
默认 16kHz 单声道（与 config 一致）。
"""

from __future__ import annotations

from pathlib import Path

from .. import config

# 录音中提示前缀（产品的「录制提示」原则：录音必须有明显反馈）。
_RECORDING_HINT = "● 正在录音…"  # ● 正在录音…


def _ensure_parent(path: Path) -> None:
    """确保目标文件的父目录存在。"""
    path.parent.mkdir(parents=True, exist_ok=True)


def record_to_wav(
    path: str | Path,
    duration_s: float,
    samplerate: int = config.SAMPLE_RATE,
    channels: int = config.CHANNELS,
) -> Path:
    """录制固定时长的麦克风音频并写入 WAV 文件。

    Args:
        path: 输出 WAV 文件路径，父目录不存在时自动创建。
        duration_s: 录制时长，单位秒。
        samplerate: 采样率（Hz），默认取自 config.SAMPLE_RATE。
        channels: 声道数，默认取自 config.CHANNELS。

    Returns:
        写入完成的 WAV 文件路径（Path）。

    Raises:
        ValueError: duration_s 不为正时。
    """
    if duration_s <= 0:
        raise ValueError(f"duration_s 必须为正，收到 {duration_s!r}")

    import sounddevice as sd  # 延迟导入重依赖
    import soundfile as sf

    out_path = Path(path)
    _ensure_parent(out_path)

    frames = int(round(duration_s * samplerate))

    print(f"{_RECORDING_HINT}（{duration_s:g}s，{samplerate}Hz/{channels}ch）", flush=True)
    audio = sd.rec(frames, samplerate=samplerate, channels=channels, dtype="float32")
    sd.wait()  # 阻塞到录制结束
    print("■ 录音结束", flush=True)  # ■ 录音结束

    sf.write(str(out_path), audio, samplerate)
    return out_path


class Recorder:
    """手动开关式录音器。

    start() 打开输入流并通过回调累积音频帧，stop(path) 停止并落盘为 WAV。
    适用于录制时长不确定、由用户手动控制起止的场景。
    """

    def __init__(
        self,
        samplerate: int = config.SAMPLE_RATE,
        channels: int = config.CHANNELS,
    ) -> None:
        """初始化录音器。

        Args:
            samplerate: 采样率（Hz），默认取自 config.SAMPLE_RATE。
            channels: 声道数，默认取自 config.CHANNELS。
        """
        self.samplerate = samplerate
        self.channels = channels
        self._stream = None  # sounddevice.InputStream，延迟创建
        self._frames: list = []  # 累积的音频块（numpy 数组）

    @property
    def is_recording(self) -> bool:
        """当前是否正在录音。"""
        return self._stream is not None

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        """sounddevice 输入流回调：把每个音频块复制进缓冲区。"""
        if status:
            # 上溢/下溢等状态打印出来，便于排查丢帧。
            print(f"录音状态：{status}", flush=True)
        self._frames.append(indata.copy())

    def start(self) -> None:
        """开始录音：打开输入流并开始累积帧。

        Raises:
            RuntimeError: 已在录音中（重复调用 start）时。
        """
        if self.is_recording:
            raise RuntimeError("已在录音中，请先调用 stop()")

        import sounddevice as sd  # 延迟导入重依赖

        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()
        print(f"{_RECORDING_HINT}（{self.samplerate}Hz/{self.channels}ch，手动停止）", flush=True)

    def stop(self, path: str | Path) -> Path:
        """停止录音并把累积的音频写入 WAV 文件。

        Args:
            path: 输出 WAV 文件路径，父目录不存在时自动创建。

        Returns:
            写入完成的 WAV 文件路径（Path）。

        Raises:
            RuntimeError: 当前未在录音（未调用 start）时。
        """
        if not self.is_recording:
            raise RuntimeError("当前未在录音，请先调用 start()")

        import numpy as np  # numpy 随 sounddevice 提供，延迟导入
        import soundfile as sf

        stream = self._stream
        self._stream = None
        stream.stop()
        stream.close()
        print("■ 录音结束", flush=True)  # ■ 录音结束

        out_path = Path(path)
        _ensure_parent(out_path)

        if self._frames:
            audio = np.concatenate(self._frames, axis=0)
        else:
            # 没有采到任何帧时写一个空音频，避免 soundfile 报错。
            audio = np.zeros((0, self.channels), dtype="float32")
        self._frames = []

        sf.write(str(out_path), audio, self.samplerate)
        return out_path
