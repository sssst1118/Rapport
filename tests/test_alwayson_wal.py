"""跨进程 SQLite：文件库启用 WAL，避免守护进程与 serve 同时读写时 database is locked。"""

from __future__ import annotations

from rapport.storage.db import Database


def test_文件库启用WAL(tmp_path) -> None:
    path = tmp_path / "rapport.db"
    db = Database(path)
    try:
        cur = db._conn.execute("PRAGMA journal_mode")
        mode = cur.fetchone()[0]
        assert str(mode).lower() == "wal"
    finally:
        db.close()


def test_内存库不因WAL报错() -> None:
    # :memory: 不支持 WAL（会回落），构造与读写不应抛错
    db = Database(":memory:")
    try:
        cid = db.add_conversation(note="x")
        assert isinstance(cid, int)
    finally:
        db.close()
