"""MCP 工具层测试：纯逻辑（tools.py）不依赖 mcp，可在内存库上直接断言。

风格对齐 tests/test_db.py：中文测试名、纯逻辑、内存库造数据。
覆盖 7 个工具的正常返回结构（含 citation 出处字段）、不存在 id 的 error 分支、
search_people 子串/大小写不敏感、search_utterances 过短 query 不崩、
relationship_graph 的 nodes/edges 结构。涉及 mcp SDK 的冒烟用 importorskip 保护。
"""

from __future__ import annotations

import pytest

from rapport.mcp import tools
from rapport.storage.db import Database


@pytest.fixture
def db():
    d = Database(":memory:")
    yield d
    d.close()


@pytest.fixture
def seeded(db: Database):
    """造人物、对话、话语、标注，返回 (db, ids)。"""
    wo = db.add_person("我", relation="自己")
    wang = db.add_person("老王", relation="同事")
    li = db.add_person("Alice", relation="朋友")
    cid = db.add_conversation(note="午饭闲聊")
    u1 = db.add_utterance(
        cid, text="你好啊老王", speaker_label="A", person_id=wo, start_ms=0, end_ms=500
    )
    u2 = db.add_utterance(
        cid, text="最近项目进度怎么样", speaker_label="B", person_id=wang,
        start_ms=500, end_ms=1200,
    )
    db.add_annotation(u1, type="tag", value="重要")
    # 第二段对话：老王 + Alice 共同在场（用于关系图共现连线）
    cid2 = db.add_conversation(note="散步")
    db.add_utterance(cid2, text="周末爬山吗", speaker_label="A", person_id=wang)
    db.add_utterance(cid2, text="好啊一起去", speaker_label="B", person_id=li)
    return db, {
        "wo": wo, "wang": wang, "li": li,
        "cid": cid, "cid2": cid2, "u1": u1, "u2": u2,
    }


# ---- list_people ---------------------------------------------------------


def test_列出全部人物含计数(seeded) -> None:
    db, ids = seeded
    people = tools.list_people(db)
    names = {p["name"] for p in people}
    assert names == {"我", "老王", "Alice"}
    wang = next(p for p in people if p["name"] == "老王")
    assert wang["id"] == ids["wang"]
    assert wang["relation"] == "同事"
    # 老王在两段对话里各一句
    assert wang["utterance_count"] == 2
    assert wang["conversation_count"] == 2
    assert "avatar" in wang


# ---- search_people -------------------------------------------------------


def test_按名字子串查人(seeded) -> None:
    db, _ = seeded
    hits = tools.search_people(db, "王")
    assert [p["name"] for p in hits] == ["老王"]


def test_按名字大小写不敏感(seeded) -> None:
    db, _ = seeded
    hits = tools.search_people(db, "alice")
    assert [p["name"] for p in hits] == ["Alice"]


def test_查无此人返回空列表(seeded) -> None:
    db, _ = seeded
    assert tools.search_people(db, "查无此人") == []


# ---- get_person ----------------------------------------------------------


def test_单人详情含话语出处(seeded) -> None:
    db, ids = seeded
    res = tools.get_person(db, ids["wang"])
    assert res["person"]["id"] == ids["wang"]
    assert res["person"]["name"] == "老王"
    utts = res["utterances"]
    assert len(utts) == 2
    first = utts[0]
    # citation 出处字段齐全
    for field in ("utterance_id", "conversation_id", "speaker_label", "text",
                  "start_ms", "end_ms"):
        assert field in first


def test_取不存在的人返回error不抛异常(seeded) -> None:
    db, _ = seeded
    res = tools.get_person(db, 999999)
    assert res["error"] == "person not found"
    assert res["person_id"] == 999999


# ---- get_conversation ----------------------------------------------------


def test_对话详情含参与者话语标注(seeded) -> None:
    db, ids = seeded
    res = tools.get_conversation(db, ids["cid"])
    conv = res["conversation"]
    assert conv["id"] == ids["cid"]
    assert conv["note"] == "午饭闲聊"
    assert "started_at" in conv
    parts = {p["name"] for p in res["participants"]}
    assert parts == {"我", "老王"}
    utts = res["utterances"]
    assert len(utts) == 2
    u1 = utts[0]
    for field in ("utterance_id", "person_id", "speaker_label", "text",
                  "start_ms", "end_ms", "annotations"):
        assert field in u1
    # u1 带一条 tag 标注
    assert u1["annotations"][0]["value"] == "重要"


def test_取不存在的对话返回error(seeded) -> None:
    db, _ = seeded
    res = tools.get_conversation(db, 999999)
    assert res["error"] == "conversation not found"
    assert res["conversation_id"] == 999999


# ---- list_conversations --------------------------------------------------


def test_列出对话含计数与参与者(seeded) -> None:
    db, ids = seeded
    convs = tools.list_conversations(db)
    by_id = {c["id"]: c for c in convs}
    assert ids["cid"] in by_id
    c = by_id[ids["cid"]]
    assert c["note"] == "午饭闲聊"
    assert "started_at" in c
    assert c["utterance_count"] == 2
    names = {p["name"] for p in c["participants"]}
    assert names == {"我", "老王"}


# ---- relationship_graph --------------------------------------------------


def test_关系图节点与连线(seeded) -> None:
    db, ids = seeded
    graph = tools.relationship_graph(db)
    node_ids = {n["id"] for n in graph["nodes"]}
    assert {ids["wo"], ids["wang"], ids["li"]} <= node_ids
    wang_node = next(n for n in graph["nodes"] if n["id"] == ids["wang"])
    assert wang_node["utterance_count"] == 2
    assert wang_node["conversation_count"] == 2
    # 第一段对话「我+老王」共现一条边，第二段「老王+Alice」共现一条边
    edge_pairs = {
        tuple(sorted((e["source"], e["target"]))): e["weight"]
        for e in graph["edges"]
    }
    assert edge_pairs[tuple(sorted((ids["wo"], ids["wang"])))] == 1
    assert edge_pairs[tuple(sorted((ids["wang"], ids["li"])))] == 1


# ---- search_utterances ---------------------------------------------------


def test_全文检索话语带出处(seeded) -> None:
    db, ids = seeded
    hits = tools.search_utterances(db, "项目进")
    assert len(hits) == 1
    h = hits[0]
    assert "项目" in h["text"]
    for field in ("utterance_id", "conversation_id", "person_id",
                  "speaker_label", "text", "start_ms", "end_ms"):
        assert field in h
    assert h["utterance_id"] == ids["u2"]


def test_过短query不崩(seeded) -> None:
    db, _ = seeded
    # 中文 <3 字 trigram 无法构造 token，FTS 会报错；工具应吞掉
    res = tools.search_utterances(db, "项")
    assert res == [] or (isinstance(res, dict) and "error" in res)


# ---- server.py 冒烟（mcp 已装才跑） --------------------------------------


def test_server_注册全部7个工具() -> None:
    import asyncio

    pytest.importorskip("mcp")
    from rapport.mcp import server

    mcp_app = server.build_server(db_path=":memory:")
    tool_names = {t.name for t in asyncio.run(mcp_app.list_tools())}
    assert tool_names == {
        "list_people",
        "search_people",
        "get_person",
        "get_conversation",
        "list_conversations",
        "relationship_graph",
        "search_utterances",
    }
