"""说话人分离子包：抽象基类 + 零依赖默认实现 + 工厂。"""

from __future__ import annotations

from ..config import _env
from .base import Diarizer

# 选用的分离实现：single 表示零依赖单说话人。
DIARIZER: str = _env("DIARIZER", "single")


def get_diarizer() -> Diarizer:
    """按 RAPPORT_DIARIZER 配置返回对应的分离器实现。

    Returns:
        Diarizer 实例。

    Raises:
        ValueError: DIARIZER 取值不被支持时。
    """
    if DIARIZER == "single":
        from .single_speaker import SingleSpeakerDiarizer

        return SingleSpeakerDiarizer()
    raise ValueError(f"不支持的 DIARIZER 取值：{DIARIZER!r}")


__all__ = ["Diarizer", "get_diarizer"]
