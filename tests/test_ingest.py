"""ingest_audio 入库管线测试：用假转写器/分离器 + 内存库，不碰重依赖。"""

from __future__ import annotations

from rapport.ingest import ingest_audio
from rapport.storage.db import Database
from rapport.transcribe.base import Segment


class _假转写器:
    """返回固定片段（无说话人标签）的假转写器。"""

    def __init__(self, segments: list[Segment]) -> None:
        self._segments = segments
        self.收到的路径: str | None = None

    def transcribe(self, audio_path: str) -> list[Segment]:
        self.收到的路径 = audio_path
        return self._segments


class _假分离器:
    """轮流给每个片段贴 A/B 标签的假分离器。"""

    def __init__(self) -> None:
        self.收到的路径: str | None = None

    def diarize(self, audio_path: str, segments: list[Segment]) -> list[Segment]:
        self.收到的路径 = audio_path
        labels = ["A", "B"]
        return [
            Segment(
                text=seg.text,
                start_ms=seg.start_ms,
                end_ms=seg.end_ms,
                speaker_label=labels[i % len(labels)],
            )
            for i, seg in enumerate(segments)
        ]


def test_入库建对话并写入正确话语() -> None:
    db = Database()
    try:
        segs = [
            Segment(text="你好世界", start_ms=0, end_ms=1000),
            Segment(text="再见啦朋友", start_ms=1000, end_ms=2000),
        ]
        transcriber = _假转写器(segs)
        diarizer = _假分离器()

        cid = ingest_audio(
            "fake.wav",
            db,
            transcriber=transcriber,
            diarizer=diarizer,
            note="测试备注",
        )

        assert isinstance(cid, int)
        # 注入的假对象都拿到了音频路径。
        assert transcriber.收到的路径 == "fake.wav"
        assert diarizer.收到的路径 == "fake.wav"

        rows = db.get_utterances(cid)
        assert len(rows) == 2
        assert [r["text"] for r in rows] == ["你好世界", "再见啦朋友"]
        # 分离器赋的说话人标签被正确写库。
        assert [r["speaker_label"] for r in rows] == ["A", "B"]
        assert [r["start_ms"] for r in rows] == [0, 1000]
    finally:
        db.close()


def test_空转写不报错且无话语() -> None:
    db = Database()
    try:
        cid = ingest_audio(
            "empty.wav",
            db,
            transcriber=_假转写器([]),
            diarizer=_假分离器(),
        )
        assert db.get_utterances(cid) == []
    finally:
        db.close()
