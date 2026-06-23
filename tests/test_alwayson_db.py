"""按天容器 DB 辅助方法测试：取或建「当天」conversation。

纯内存库，不碰硬件。覆盖：同一天续写同一个 conversation；不同天各自独立；
新建时写入 audio_path 与 note 日期标记。
"""

from __future__ import annotations

from rapport.storage.db import Database


def test_首次取或建_新建当天对话() -> None:
    db = Database()
    try:
        cid = db.get_or_create_daily_conversation(
            "2026-06-23", audio_path="data/audio/2026-06-23.wav"
        )
        assert isinstance(cid, int)
        row = db.get_conversation(cid)
        assert row["audio_path"] == "data/audio/2026-06-23.wav"
        assert "2026-06-23" in (row["note"] or "")
    finally:
        db.close()


def test_同一天再次取_续写同一个对话不新建() -> None:
    db = Database()
    try:
        c1 = db.get_or_create_daily_conversation(
            "2026-06-23", audio_path="data/audio/2026-06-23.wav"
        )
        c2 = db.get_or_create_daily_conversation(
            "2026-06-23", audio_path="data/audio/2026-06-23.wav"
        )
        assert c1 == c2
        # 全库仍只有 1 个对话
        assert len(db.list_conversations()) == 1
    finally:
        db.close()


def test_不同天各自独立对话() -> None:
    db = Database()
    try:
        c1 = db.get_or_create_daily_conversation(
            "2026-06-23", audio_path="data/audio/2026-06-23.wav"
        )
        c2 = db.get_or_create_daily_conversation(
            "2026-06-24", audio_path="data/audio/2026-06-24.wav"
        )
        assert c1 != c2
        assert len(db.list_conversations()) == 2
    finally:
        db.close()


def test_普通对话不会被当天查询误命中() -> None:
    db = Database()
    try:
        # 一个跟「常驻记录」无关的普通对话（即便 note 含日期数字也不该命中）
        db.add_conversation(audio_path="x.wav", note="午饭聊天 2026-06-23")
        cid = db.get_or_create_daily_conversation(
            "2026-06-23", audio_path="data/audio/2026-06-23.wav"
        )
        # 应新建一个常驻容器，而不是复用那条普通对话
        assert len(db.list_conversations()) == 2
        row = db.get_conversation(cid)
        assert row["audio_path"] == "data/audio/2026-06-23.wav"
    finally:
        db.close()
