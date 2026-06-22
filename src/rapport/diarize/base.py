"""说话人分离契约：分离器抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..transcribe.base import Segment


class Diarizer(ABC):
    """说话人分离器抽象基类：给转写片段标注说话人标签。"""

    @abstractmethod
    def diarize(self, audio_path: str, segments: list[Segment]) -> list[Segment]:
        """为转写片段标注说话人标签。

        Args:
            audio_path: 原始音频文件路径，供真实实现重新分析音频用。
            segments: 转写得到的片段列表。

        Returns:
            带 speaker_label 的新片段列表。
        """
        raise NotImplementedError
