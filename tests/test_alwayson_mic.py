"""真实麦克风音频源适配器测试：不开真声卡，注入假 InputStream 工厂验证接线。

只验「sounddevice 回调 → 引擎 frame 回调」的转接与起停，不碰真硬件。
真硬件路径只在 rapport watch 里走。
"""

from __future__ import annotations

import numpy as np

from rapport.alwayson.mic import MicAudioSource


class _假流:
    """假 InputStream：记录回调、可手动触发，start/stop/close 计数。"""

    def __init__(self, *, callback, **kwargs) -> None:  # noqa: ANN003
        self.callback = callback
        self.kwargs = kwargs
        self.started = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.started = False

    def close(self) -> None:
        self.closed = True

    def fire(self, indata: np.ndarray) -> None:
        """模拟 sounddevice 回调：(indata, frames, time, status)。"""
        self.callback(indata, len(indata), None, None)


def test_麦克风源把帧转给引擎回调() -> None:
    made: list[_假流] = []

    def factory(**kwargs):  # noqa: ANN003
        s = _假流(**kwargs)
        made.append(s)
        return s

    src = MicAudioSource(samplerate=16000, channels=1, device=None, stream_factory=factory)
    received: list[np.ndarray] = []
    src.start(lambda f: received.append(f))

    assert len(made) == 1
    assert made[0].started is True
    # sounddevice 给的是 (frames, channels) 二维；适配器应摊平成一维 float32
    made[0].fire(np.array([[0.1], [0.2], [0.3]], dtype="float32"))
    assert len(received) == 1
    assert received[0].ndim == 1
    assert np.allclose(received[0], [0.1, 0.2, 0.3], atol=1e-6)

    src.stop()
    assert made[0].started is False
    assert made[0].closed is True


def test_未start时stop不抛错() -> None:
    src = MicAudioSource(stream_factory=lambda **k: _假流(**k))
    src.stop()  # 没 start 过也不应抛
