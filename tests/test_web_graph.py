"""关系图与复盘端点的后端测试。自带最小夹具，风格对齐 tests/test_web.py。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from rapport.storage.db import Database
from rapport.web import create_app


@pytest.fixture
def client(tmp_path):
    """我+老王同段对话（应相连），小李独自一段（应孤立）。"""
    db = Database(tmp_path / "g.db")
    wo = db.add_person("我", relation="自己")
    wang = db.add_person("老王", relation="同事")
    li = db.add_person("小李", relation="实习生")
    c1 = db.add_conversation(note="午饭")
    db.add_utterance(c1, text="一", speaker_label="A", person_id=wo)
    db.add_utterance(c1, text="二", speaker_label="B", person_id=wang)
    c2 = db.add_conversation(note="散步")
    db.add_utterance(c2, text="三", speaker_label="A", person_id=li)
    app = create_app(db_path=tmp_path / "g.db", repo_root=tmp_path)
    cl = TestClient(app)
    yield cl, {"wo": wo, "wang": wang, "li": li}
    db.close()


def test_关系图节点覆盖全部人物(client) -> None:
    cl, ids = client
    g = cl.get("/api/graph").json()
    assert {n["id"] for n in g["nodes"]} == set(ids.values())


def test_共现推断我与老王相连而小李孤立(client) -> None:
    cl, ids = client
    g = cl.get("/api/graph").json()
    pairs = {
        (min(e["source"], e["target"]), max(e["source"], e["target"])): e["weight"]
        for e in g["edges"]
    }
    key = (min(ids["wo"], ids["wang"]), max(ids["wo"], ids["wang"]))
    assert pairs.get(key) == 1
    # 小李没和任何人同段对话 → 不出现在任何连线里
    assert all(ids["li"] not in (e["source"], e["target"]) for e in g["edges"])


def test_复盘端点未配置时needs_setup(client) -> None:
    cl, _ = client
    r = cl.post("/api/review", json={"scope": "conversation", "id": 1})
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "interpretation"
    # 默认未配置语言模型，复盘端点返回 needs_setup 信封（仍 200）。
    assert body["status"] == "needs_setup"
