"""单说话人分离器：零依赖默认实现，把全部片段标为同一说话人。"""

from __future__ import annotations

from dataclasses import replace

from ..transcribe.base import Segment
from .base import Diarizer


class SingleSpeakerDiarizer(Diarizer):
    """假定音频只有一位说话人，把所有片段统一标为 "A"。"""

    def diarize(self, audio_path: str, segments: list[Segment]) -> list[Segment]:
        """把每个片段的 speaker_label 统一标成 "A"。

        不修改传入的原片段对象，返回新的 Segment 列表，
        保留各片段的 text 与时间戳。空列表返回空列表。

        Args:
            audio_path: 音频路径（本实现不使用，仅为契约一致）。
            segments: 待标注的片段列表。

        Returns:
            speaker_label 均为 "A" 的新片段列表。
        """
        return [replace(seg, speaker_label="A") for seg in segments]
