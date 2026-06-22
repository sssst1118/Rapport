"""Transcriber 接口契约测试：用 FakeTranscriber 验证，不依赖 faster-whisper。"""

from __future__ import annotations

from rapport.transcribe.base import Segment, Transcriber
from rapport.transcribe.text import segments_to_text


class FakeTranscriber(Transcriber):
    """返回固定 Segment 列表的假转写器，仅用于测试接口契约。"""

    def transcribe(self, audio_path: str) -> list[Segment]:
        """忽略输入，返回预置的两段结果。"""
        return [
            Segment(text="第一句", start_ms=0, end_ms=1000),
            Segment(text="第二句", start_ms=1000, end_ms=2000, speaker_label="A"),
        ]


def test_fake满足接口() -> None:
    transcriber = FakeTranscriber()
    assert isinstance(transcriber, Transcriber)


def test_fake返回segment列表() -> None:
    segments = FakeTranscriber().transcribe("任意路径.wav")
    assert isinstance(segments, list)
    assert all(isinstance(s, Segment) for s in segments)
    assert len(segments) == 2


def test_fake结果可喂给segments_to_text() -> None:
    segments = FakeTranscriber().transcribe("任意路径.wav")
    assert segments_to_text(segments) == "第一句\n第二句"


def test_抽象基类不可直接实例化() -> None:
    import pytest

    with pytest.raises(TypeError):
        Transcriber()  # type: ignore[abstract]
