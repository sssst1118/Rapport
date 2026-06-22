"""把转写片段拼接为可读文本的纯函数。"""

from __future__ import annotations

from .base import Segment


def segments_to_text(segments: list[Segment]) -> str:
    """把多段转写结果拼成一段可读文本。

    规则：每段取 text.strip()，丢弃 strip 后为空的段，
    用换行连接，整体再 strip。

    Args:
        segments: 转写片段列表。

    Returns:
        拼接后的可读文本。
    """
    lines = [seg.text.strip() for seg in segments]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()
