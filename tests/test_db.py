"""SQLite 存储层测试：建库、入库、按对话/人查询、全文检索、改说话人归属。

全部跑在内存库（:memory:）上，无需任何重依赖。
"""

from __future__ import annotations

import pytest

from rapport.storage.db import Database
from rapport.transcribe.base import Segment


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()


def test_新建对话返回自增id(db: Database) -> None:
    cid = db.add_conversation(note="测试对话")
    assert isinstance(cid, int)
    assert cid > 0


def test_入库与按对话取话语保持顺序(db: Database) -> None:
    cid = db.add_conversation()
    db.add_utterance(cid, text="你好啊老王", speaker_label="A")
    db.add_utterance(cid, text="最近怎么样", speaker_label="B")
    rows = db.get_utterances(cid)
    assert [r["text"] for r in rows] == ["你好啊老王", "最近怎么样"]
    assert [r["speaker_label"] for r in rows] == ["A", "B"]


def test_批量写入转写片段(db: Database) -> None:
    cid = db.add_conversation()
    segs = [
        Segment(text="hello", start_ms=0, end_ms=500, speaker_label="A"),
        Segment(text="world", start_ms=500, end_ms=1000, speaker_label="A"),
    ]
    ids = db.add_segments(cid, segs)
    assert len(ids) == 2
    rows = db.get_utterances(cid)
    assert rows[0]["start_ms"] == 0
    assert rows[1]["text"] == "world"
    assert rows[1]["end_ms"] == 1000


def test_按人取话语只返回该人的(db: Database) -> None:
    cid = db.add_conversation()
    pid = db.add_person("老王")
    db.add_utterance(cid, text="我是老王说的", person_id=pid)
    db.add_utterance(cid, text="这句还没归属")
    rows = db.get_utterances_for_person(pid)
    assert [r["text"] for r in rows] == ["我是老王说的"]


def test_修改话语的说话人归属(db: Database) -> None:
    cid = db.add_conversation()
    pid = db.add_person("老王")
    uid = db.add_utterance(cid, text="把这句改归到老王名下")
    assert db.get_utterances_for_person(pid) == []
    db.set_utterance_person(uid, pid)
    rows = db.get_utterances_for_person(pid)
    assert len(rows) == 1
    assert rows[0]["id"] == uid


def test_全文检索中文(db: Database) -> None:
    cid = db.add_conversation()
    db.add_utterance(cid, text="我们今天聊了项目进度")
    db.add_utterance(cid, text="周末一起去爬山吧")
    hits = db.search_utterances("项目进")  # trigram 分词需 ≥3 字
    assert len(hits) == 1
    assert "项目" in hits[0]["text"]


def test_全文检索英文(db: Database) -> None:
    cid = db.add_conversation()
    db.add_utterance(cid, text="we discussed the project timeline")
    db.add_utterance(cid, text="let us go hiking this weekend")
    hits = db.search_utterances("project")
    assert len(hits) == 1
    assert "project" in hits[0]["text"]


def test_文件库可持久化重开(tmp_path) -> None:
    path = tmp_path / "rapport.db"
    d1 = Database(path)
    cid = d1.add_conversation(note="持久化")
    d1.add_utterance(cid, text="重开还在不在")
    d1.close()

    d2 = Database(path)
    rows = d2.get_utterances(cid)
    assert [r["text"] for r in rows] == ["重开还在不在"]
    d2.close()
