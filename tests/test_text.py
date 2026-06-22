"""segments_to_text 纯逻辑测试：不依赖 faster-whisper。"""

from __future__ import annotations

from rapport.transcribe.base import Segment
from rapport.transcribe.text import segments_to_text


def _seg(text: str) -> Segment:
    """构造一个仅关心 text 的 Segment。"""
    return Segment(text=text, start_ms=0, end_ms=0)


def test_多段拼接() -> None:
    segments = [_seg("你好"), _seg("世界"), _seg("再见")]
    assert segments_to_text(segments) == "你好\n世界\n再见"


def test_空段被丢弃() -> None:
    segments = [_seg("第一段"), _seg(""), _seg("   "), _seg("第二段")]
    assert segments_to_text(segments) == "第一段\n第二段"


def test_首尾空白被strip() -> None:
    segments = [_seg("  开头  "), _seg("  结尾  ")]
    assert segments_to_text(segments) == "开头\n结尾"


def test_单段() -> None:
    assert segments_to_text([_seg("唯一一段")]) == "唯一一段"


def test_单段含空白被strip() -> None:
    assert segments_to_text([_seg("  带空白  ")]) == "带空白"


def test_空列表返回空字符串() -> None:
    assert segments_to_text([]) == ""


def test_全空段返回空字符串() -> None:
    segments = [_seg(""), _seg("   "), _seg("\n\t")]
    assert segments_to_text(segments) == ""
