"""diarize 子包单测：SingleSpeaker + 纯对齐算法 + 工厂 + 可选依赖边界（无重依赖）。"""

from __future__ import annotations

import pytest

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


# ---- 纯对齐算法 assign_speaker_labels（TDD 核心，零 torch 依赖） ----------

from rapport.diarize.align import assign_speaker_labels  # noqa: E402


def test_两说话人交替按重叠分配AB() -> None:
    segments = [
        Segment(text="句一", start_ms=0, end_ms=1000),
        Segment(text="句二", start_ms=1000, end_ms=2000),
        Segment(text="句三", start_ms=2000, end_ms=3000),
    ]
    turns = [
        ("SPEAKER_00", 0, 1000),
        ("SPEAKER_01", 1000, 2000),
        ("SPEAKER_00", 2000, 3000),
    ]
    result = assign_speaker_labels(segments, turns)
    assert [s.speaker_label for s in result] == ["A", "B", "A"]


def test_重映射按首次出现先出现的为A() -> None:
    # SPEAKER_01 先在时间轴上覆盖第一句 → 它应映射成 A（按本次结果首次出现顺序）。
    segments = [
        Segment(text="句一", start_ms=0, end_ms=1000),
        Segment(text="句二", start_ms=1000, end_ms=2000),
    ]
    turns = [
        ("SPEAKER_01", 0, 1000),
        ("SPEAKER_00", 1000, 2000),
    ]
    result = assign_speaker_labels(segments, turns)
    assert [s.speaker_label for s in result] == ["A", "B"]


def test_句子跨两个turn取重叠多的() -> None:
    # 句子 [0,1000)：与 SPEAKER_00 重叠 300ms，与 SPEAKER_01 重叠 700ms → 取 01。
    segments = [Segment(text="跨界", start_ms=0, end_ms=1000)]
    turns = [
        ("SPEAKER_00", 0, 300),
        ("SPEAKER_01", 300, 1000),
    ]
    result = assign_speaker_labels(segments, turns)
    assert result[0].speaker_label == "A"  # SPEAKER_01 是首次出现者 → A


def test_无重叠的句子标None() -> None:
    segments = [
        Segment(text="有重叠", start_ms=0, end_ms=1000),
        Segment(text="静音段", start_ms=5000, end_ms=6000),
    ]
    turns = [("SPEAKER_00", 0, 1000)]
    result = assign_speaker_labels(segments, turns)
    assert [s.speaker_label for s in result] == ["A", None]


def test_幂等同输入同输出() -> None:
    segments = [
        Segment(text="句一", start_ms=0, end_ms=1000),
        Segment(text="句二", start_ms=1000, end_ms=2000),
    ]
    turns = [
        ("SPEAKER_00", 0, 1000),
        ("SPEAKER_01", 1000, 2000),
    ]
    once = assign_speaker_labels(segments, turns)
    twice = assign_speaker_labels(once, turns)
    assert [s.speaker_label for s in once] == [s.speaker_label for s in twice]


def test_单说话人全A() -> None:
    segments = [
        Segment(text="句一", start_ms=0, end_ms=1000),
        Segment(text="句二", start_ms=1000, end_ms=2000),
    ]
    turns = [("SPEAKER_00", 0, 2000)]
    result = assign_speaker_labels(segments, turns)
    assert [s.speaker_label for s in result] == ["A", "A"]


def test_对齐不改原片段对象() -> None:
    original = Segment(text="原句", start_ms=0, end_ms=1000, speaker_label=None)
    assign_speaker_labels([original], [("SPEAKER_00", 0, 1000)])
    assert original.speaker_label is None


def test_空输入与空turns() -> None:
    assert assign_speaker_labels([], [("SPEAKER_00", 0, 1000)]) == []
    seg = Segment(text="句", start_ms=0, end_ms=1000)
    result = assign_speaker_labels([seg], [])
    assert result[0].speaker_label is None


# ---- 工厂 get_diarizer ----------------------------------------------------


def test_工厂默认single(monkeypatch: pytest.MonkeyPatch) -> None:
    import rapport.diarize as d

    monkeypatch.setattr(d, "DIARIZER", "single")
    assert isinstance(d.get_diarizer(), SingleSpeakerDiarizer)


def test_工厂未知值报错(monkeypatch: pytest.MonkeyPatch) -> None:
    import rapport.diarize as d

    monkeypatch.setattr(d, "DIARIZER", "不存在的实现")
    with pytest.raises(ValueError):
        d.get_diarizer()


def test_工厂pyannote分支(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("pyannote.audio")
    import rapport.diarize as d
    from rapport.diarize.pyannote_diarizer import PyannoteDiarizer

    monkeypatch.setattr(d, "DIARIZER", "pyannote")
    assert isinstance(d.get_diarizer(), PyannoteDiarizer)


# ---- 可选依赖边界：未装 pyannote 时构造抛清晰 ImportError ------------------


def test_导入diarize子包不炸() -> None:
    import importlib

    import rapport.diarize

    importlib.reload(rapport.diarize)  # 整包 import 不应触发任何重依赖


def test_构造PyannoteDiarizer未装时抛带指引的ImportError(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import builtins

    real_import = builtins.__import__

    def 假import(name: str, *args: object, **kwargs: object) -> object:
        if name.startswith("pyannote"):
            raise ImportError("No module named 'pyannote'")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", 假import)

    from rapport.diarize.pyannote_diarizer import PyannoteDiarizer

    with pytest.raises(ImportError) as exc:
        PyannoteDiarizer()
    msg = str(exc.value)
    assert "pyannote" in msg
    assert "diarize" in msg  # 安装指引含 extra 名
