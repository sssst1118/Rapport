"""真实麦克风音频源：把 sounddevice InputStream 回调适配成引擎的 AudioSource。

sounddevice 延迟导入（仅在不注入 stream_factory 时真正 import），未装/无声卡时
本模块仍可导入、引擎仍可构造，纯逻辑测试不受影响。真硬件路径只在 rapport watch 里走。
16kHz 单声道 float32，与 config / recorder 一致。
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from .. import config


class MicAudioSource:
    """麦克风音频源：start(callback) 打开 InputStream，回调里把帧摊平成一维转给 callback。"""

    def __init__(
        self,
        samplerate: int = config.SAMPLE_RATE,
        channels: int = config.CHANNELS,
        device: int | str | None = config.INPUT_DEVICE,
        *,
        stream_factory: Callable[..., object] | None = None,
    ) -> None:
        """构造麦克风源。

        Args:
            samplerate: 采样率（Hz）。
            channels: 声道数（引擎按单声道处理，>1 时取首声道）。
            device: 输入设备（索引/名称/None=系统默认）。
            stream_factory: 注入用的流工厂（测试）；None 时用 sd.InputStream（延迟导入）。
        """
        self.samplerate = samplerate
        self.channels = channels
        self.device = device
        self._factory = stream_factory
        self._stream = None
        self._callback: Callable[[np.ndarray], None] | None = None

    def start(self, callback: Callable[[np.ndarray], None]) -> None:
        """打开输入流，每块音频帧摊平成一维 float32 后交给 callback。

        Args:
            callback: 接收一维 float32 帧的回调（引擎的 _on_frame）。
        """
        self._callback = callback
        factory = self._factory
        if factory is None:
            import sounddevice as sd  # 延迟导入重依赖

            factory = sd.InputStream
        self._stream = factory(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="float32",
            device=self.device,
            callback=self._on_audio,
        )
        self._stream.start()

    def _on_audio(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        """sounddevice 回调：把 (frames, channels) 摊平成一维（取首声道）转给引擎。"""
        if status:
            print(f"录音状态：{status}", flush=True)
        if self._callback is None:
            return
        arr = np.asarray(indata, dtype="float32")
        if arr.ndim == 2:
            arr = arr[:, 0]  # 单声道：取首声道
        self._callback(np.ascontiguousarray(arr.reshape(-1)))

    def stop(self) -> None:
        """停止并关闭输入流；未 start 过也安全。"""
        stream = self._stream
        self._stream = None
        self._callback = None
        if stream is None:
            return
        try:
            stream.stop()
        finally:
            stream.close()
