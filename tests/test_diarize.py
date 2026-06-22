"""SingleSpeakerDiarizer 的单元测试（纯逻辑，无重依赖）。"""

from __future__ import annotations

from rapport.diarize.single_speaker import SingleSpeakerDiarizer
from rapport.transcribe.base import Segment


def test_所有片段被标为A() -> None:
    segments = [
        Segment(text="你好", start_ms=0, end_ms=1000),
        Segment(text="世界", start_ms=1000, end_ms=2000),
    ]
    result = SingleSpeakerDiarizer().diarize("dummy.wav", segments)
    assert [s.speaker_label for s in result] == ["A", "A"]


def test_文本与时间戳不变() -> None:
    segments = [
        Segment(text="第一句", start_ms=0, end_ms=500),
        Segment(text="第二句", start_ms=500, end_ms=1200, speaker_label="原标签"),
    ]
    result = SingleSpeakerDiarizer().diarize("dummy.wav", segments)
    assert [(s.text, s.start_ms, s.end_ms) for s in result] == [
        ("第一句", 0, 500),
        ("第二句", 500, 1200),
    ]


def test_空输入返回空() -> None:
    assert SingleSpeakerDiarizer().diarize("dummy.wav", []) == []


def test_原始片段不被改动() -> None:
    original = Segment(text="不可变", start_ms=0, end_ms=100, speaker_label=None)
    SingleSpeakerDiarizer().diarize("dummy.wav", [original])
    assert original.speaker_label is None
