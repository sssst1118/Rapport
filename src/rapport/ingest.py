"""入库管线：转写 → 说话人分离 → 写入 SQLite。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import config
from .diarize import get_diarizer

if TYPE_CHECKING:
    from .diarize.base import Diarizer
    from .storage.db import Database
    from .transcribe.base import Transcriber


def ingest_audio(
    audio_path: str,
    db: Database,
    transcriber: Transcriber | None = None,
    diarizer: Diarizer | None = None,
    note: str | None = None,
) -> int:
    """转写并分离一段音频，写入数据库，返回新对话 id。

    transcriber/diarizer 可注入，便于用假对象测试；缺省时按配置构造。

    Args:
        audio_path: 音频文件路径。
        db: 已打开的数据库门面。
        transcriber: 转写器；None 时用 config.get_transcriber()。
        diarizer: 分离器；None 时用 get_diarizer()。
        note: 对话备注，可空。

    Returns:
        新建对话的 id。
    """
    transcriber = transcriber or config.get_transcriber()
    diarizer = diarizer or get_diarizer()

    segments = transcriber.transcribe(audio_path)
    segments = diarizer.diarize(audio_path, segments)

    cid = db.add_conversation(audio_path=audio_path, note=note)
    db.add_segments(cid, segments)
    return cid
