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
    if DIARIZER == "pyannote":
        # 延迟导入：未装可选依赖 pyannote.audio 时，整包 import 仍正常，
        # 只有真正选用 pyannote 时才尝试加载（构造内未装则抛带指引的 ImportError）。
        from .pyannote_diarizer import PyannoteDiarizer

        return PyannoteDiarizer()
    raise ValueError(f"不支持的 DIARIZER 取值：{DIARIZER!r}")


__all__ = ["Diarizer", "get_diarizer"]
