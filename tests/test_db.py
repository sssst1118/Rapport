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


# ---- M3：以人为中心的查询 -------------------------------------------------


def test_列出全部人物(db: Database) -> None:
    db.add_person("老王")
    db.add_person("小李")
    rows = db.list_persons()
    assert {r["name"] for r in rows} == {"老王", "小李"}


def test_按id取单个人物_不存在返回None(db: Database) -> None:
    pid = db.add_person("老王", relation="同事")
    row = db.get_person(pid)
    assert row is not None
    assert row["name"] == "老王"
    assert row["relation"] == "同事"
    assert db.get_person(99999) is None


def test_按id取单个对话_含音频路径与备注(db: Database) -> None:
    cid = db.add_conversation(audio_path="/tmp/a.wav", note="午饭")
    row = db.get_conversation(cid)
    assert row is not None
    assert row["audio_path"] == "/tmp/a.wav"
    assert row["note"] == "午饭"
    assert db.get_conversation(99999) is None


def test_列出对话最近优先(db: Database) -> None:
    c1 = db.add_conversation(note="先")
    c2 = db.add_conversation(note="后")
    rows = db.list_conversations()
    # 默认按 started_at、id 倒序：同一时刻入库时较大的 id 在前
    assert [r["id"] for r in rows] == [c2, c1]


def test_对话在场者只含有归属话语的人按首次出现排序(db: Database) -> None:
    cid = db.add_conversation()
    wang = db.add_person("老王")
    li = db.add_person("小李")
    # 小李先开口、老王后开口、再加一句未归属
    db.add_utterance(cid, text="小李先说", person_id=li, start_ms=0)
    db.add_utterance(cid, text="老王后说", person_id=wang, start_ms=100)
    db.add_utterance(cid, text="没归属的", start_ms=200)
    rows = db.get_persons_in_conversation(cid)
    assert [r["name"] for r in rows] == ["小李", "老王"]


def test_增查三类标注(db: Database) -> None:
    cid = db.add_conversation()
    uid = db.add_utterance(cid, text="这句很重要")
    db.add_annotation(uid, type="tag", value="重要")
    db.add_annotation(uid, type="note", value="当时我有点意外")
    rows = db.get_annotations(uid)
    pairs = {(r["type"], r["value"]) for r in rows}
    assert pairs == {("tag", "重要"), ("note", "当时我有点意外")}


def test_编辑话语文字_全文检索随之更新(db: Database) -> None:
    cid = db.add_conversation()
    uid = db.add_utterance(cid, text="我们聊了天气情况")
    db.update_utterance_text(uid, "我们聊了项目进度")
    rows = db.get_utterances(cid)
    assert rows[0]["text"] == "我们聊了项目进度"
    # FTS 触发器应让旧词检索不到、新词检索得到
    assert db.search_utterances("天气情") == []
    assert len(db.search_utterances("项目进")) == 1


def test_整段说话人改归属_只动该标签且返回条数(db: Database) -> None:
    cid = db.add_conversation()
    wang = db.add_person("老王")
    db.add_utterance(cid, text="A第一句", speaker_label="A", start_ms=0)
    db.add_utterance(cid, text="B插一句", speaker_label="B", start_ms=100)
    db.add_utterance(cid, text="A第二句", speaker_label="A", start_ms=200)
    n = db.relabel_speaker(cid, "A", wang)
    assert n == 2
    wang_texts = [r["text"] for r in db.get_utterances_for_person(wang)]
    assert wang_texts == ["A第一句", "A第二句"]


def test_整段说话人改归属_不跨对话(db: Database) -> None:
    c1 = db.add_conversation()
    c2 = db.add_conversation()
    wang = db.add_person("老王")
    db.add_utterance(c1, text="对话1的A", speaker_label="A")
    db.add_utterance(c2, text="对话2的A", speaker_label="A")
    db.relabel_speaker(c1, "A", wang)
    texts = [r["text"] for r in db.get_utterances_for_person(wang)]
    assert texts == ["对话1的A"]
