"""转写契约：转写片段数据类与转写器抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Segment:
    """一段转写结果。

    Attributes:
        text: 该段的文本内容。
        start_ms: 起始时间，单位毫秒。
        end_ms: 结束时间，单位毫秒。
        speaker_label: 说话人标签，未知时为 None。
    """

    text: str
    start_ms: int
    end_ms: int
    speaker_label: str | None = None


class Transcriber(ABC):
    """转写器抽象基类：把音频文件转写为有序的 Segment 列表。"""

    @abstractmethod
    def transcribe(self, audio_path: str) -> list[Segment]:
        """把指定路径的音频文件转写为转写片段列表。

        Args:
            audio_path: 音频文件路径。

        Returns:
            按时间排序的 Segment 列表。
        """
        raise NotImplementedError
