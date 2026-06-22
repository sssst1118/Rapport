"""按需分析层测试（M4）：可插拔 LLM 抽象 + 引用解析 + 端点三态。

全部用 fake provider（确定性、不联网），纯逻辑。风格对齐 tests/test_web.py：
中文测试名、内存/文件库注入、FastAPI TestClient。

覆盖：
① fake provider 的 generate_json 按 schema 产出可预测结构；
② analyze_person 把 quote_utterance_ids 解析成完整 Citation（含
   conversation_id/text/person_name），并丢弃指向不存在 id 的引用；
③ 经 TestClient 打 /api/people/{id}/analysis：未设 provider 时
   status==needs_setup；设 fake 时 status==ready 且字段齐全。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from rapport.analysis import get_provider
from rapport.analysis.analyze import analyze_person
from rapport.analysis.llm.fake_provider import FakeProvider
from rapport.storage.db import Database
from rapport.web import create_app

# 分析层用的结构化输出 schema（与 analyze.py 对齐）。
_SCHEMA = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "point": {"type": "string"},
                    "quote_utterance_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                },
                "required": ["point", "quote_utterance_ids"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["overview", "findings"],
    "additionalProperties": False,
}


@pytest.fixture
def seeded(tmp_path):
    """造一个有人物、对话、话语的文件库，返回 (db, 关键 id, tmp_path)。

    与 test_web.py 一致：web 层把连接封闭到工作线程，测试这边用自己的句柄
    读同一个文件；两端通过同一文件协作。
    """
    db = Database(tmp_path / "rapport.db")
    wo = db.add_person("我", relation="自己")
    wang = db.add_person("老王", relation="同事")
    cid = db.add_conversation(note="午饭闲聊")
    u1 = db.add_utterance(
        cid, text="最近项目压力挺大的", speaker_label="B", person_id=wang,
        start_ms=0, end_ms=900,
    )
    u2 = db.add_utterance(
        cid, text="下周我把方案给你", speaker_label="B", person_id=wang,
        start_ms=900, end_ms=1800,
    )
    u3 = db.add_utterance(
        cid, text="好的辛苦了", speaker_label="A", person_id=wo,
        start_ms=1800, end_ms=2300,
    )
    ids = {"wo": wo, "wang": wang, "cid": cid, "u1": u1, "u2": u2, "u3": u3}
    yield db, ids, tmp_path
    db.close()


# ---- ① fake provider ----------------------------------------------------


def test_fake_provider_按schema产出可预测结构() -> None:
    provider = FakeProvider()
    user = "[12] 老王: 最近项目压力挺大的\n[13] 老王: 下周我把方案给你"
    out = provider.generate_json("分析这个人的沟通风格", user, _SCHEMA)
    # 顶层结构符合 schema
    assert isinstance(out, dict)
    assert set(out) == {"overview", "findings"}
    assert isinstance(out["overview"], str) and out["overview"]
    assert isinstance(out["findings"], list) and out["findings"]
    f0 = out["findings"][0]
    assert set(f0) == {"point", "quote_utterance_ids"}
    # 引用的 id 必须来自提示里真实出现的 id（这里是 12/13）
    assert f0["quote_utterance_ids"]
    assert set(f0["quote_utterance_ids"]) <= {12, 13}
    # 诚实标注：point 文案以「（示例）」前缀明示是占位、非真模型产出
    assert f0["point"].startswith("（示例）")


def test_fake_provider_无可用id时引用为空() -> None:
    provider = FakeProvider()
    out = provider.generate_json("任务", "没有任何方括号编号的纯文本", _SCHEMA)
    assert out["findings"][0]["quote_utterance_ids"] == []


# ---- ② 引用解析为完整 Citation ------------------------------------------


def test_analyze_person_把id解析成完整citation(seeded) -> None:
    db, ids, _ = seeded
    provider = FakeProvider()
    result = analyze_person(db, provider, ids["wang"])
    assert set(result) == {"overview", "findings"}
    assert result["findings"]
    quotes = result["findings"][0]["quotes"]
    assert quotes, "应至少有一条引用"
    q = quotes[0]
    # Citation 字段齐全
    assert set(q) >= {
        "utterance_id", "conversation_id", "text",
        "start_ms", "end_ms", "speaker_label", "person_name",
    }
    # 内容正确：来自老王的话语
    assert q["conversation_id"] == ids["cid"]
    assert q["person_name"] == "老王"
    assert q["text"] in {"最近项目压力挺大的", "下周我把方案给你"}
    assert q["utterance_id"] in {ids["u1"], ids["u2"]}


def test_未归属话语的person_name为None(seeded) -> None:
    db, ids, _ = seeded
    # 新增一句无归属的话语
    extra = db.add_utterance(ids["cid"], text="路过插一句", start_ms=2400, end_ms=2600)
    provider = FakeProvider()
    # 直接走划选分析，确保覆盖到这条 utterance
    from rapport.analysis.analyze import analyze_selection

    result = analyze_selection(db, provider, [extra])
    q = result["findings"][0]["quotes"][0]
    assert q["utterance_id"] == extra
    assert q["person_name"] is None


def test_丢弃指向不存在id的引用(seeded) -> None:
    db, ids, _ = seeded

    class GhostProvider:
        """返回一个真实 id + 一个不存在 id，验证后端丢弃幽灵引用。"""

        def generate_json(self, system, user, schema):
            return {
                "overview": "概览",
                "findings": [
                    {"point": "判断", "quote_utterance_ids": [ids["u1"], 999999]}
                ],
            }

    result = analyze_person(db, GhostProvider(), ids["wang"])
    quotes = result["findings"][0]["quotes"]
    # 只剩真实存在的那条，幽灵 id 被丢弃
    assert len(quotes) == 1
    assert quotes[0]["utterance_id"] == ids["u1"]


# ---- get_provider 配置切换 ----------------------------------------------


def test_get_provider_none返回None(monkeypatch) -> None:
    from rapport import config

    monkeypatch.setattr(config, "LLM_PROVIDER", "none")
    assert get_provider() is None


def test_get_provider_fake返回fake实例(monkeypatch) -> None:
    from rapport import config

    monkeypatch.setattr(config, "LLM_PROVIDER", "fake")
    assert isinstance(get_provider(), FakeProvider)


# ---- ③ 端点三态 ---------------------------------------------------------


def test_人物分析未配置provider时needs_setup(seeded, monkeypatch) -> None:
    db, ids, tmp_path = seeded
    from rapport import config

    monkeypatch.setattr(config, "LLM_PROVIDER", "none")
    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    r = client.get(f"/api/people/{ids['wang']}/analysis")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "interpretation"
    assert body["status"] == "needs_setup"
    assert body["data"] is None
    assert isinstance(body["message"], str) and body["message"]


def test_人物分析fake_provider时ready且字段齐全(seeded, monkeypatch) -> None:
    db, ids, tmp_path = seeded
    from rapport import config

    monkeypatch.setattr(config, "LLM_PROVIDER", "fake")
    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    r = client.get(f"/api/people/{ids['wang']}/analysis")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "interpretation"
    assert body["status"] == "ready"
    data = body["data"]
    assert isinstance(data["overview"], str)
    assert data["findings"]
    q0 = data["findings"][0]["quotes"][0]
    assert set(q0) >= {
        "utterance_id", "conversation_id", "text",
        "start_ms", "end_ms", "speaker_label", "person_name",
    }
    assert q0["person_name"] == "老王"


def test_对话摘要fake_provider时ready(seeded, monkeypatch) -> None:
    db, ids, tmp_path = seeded
    from rapport import config

    monkeypatch.setattr(config, "LLM_PROVIDER", "fake")
    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    r = client.get(f"/api/conversations/{ids['cid']}/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["data"]["findings"]


def test_划选分析fake_provider时ready(seeded, monkeypatch) -> None:
    db, ids, tmp_path = seeded
    from rapport import config

    monkeypatch.setattr(config, "LLM_PROVIDER", "fake")
    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    r = client.post("/api/analyze", json={"utterance_ids": [ids["u1"], ids["u2"]]})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    q0 = body["data"]["findings"][0]["quotes"][0]
    assert q0["utterance_id"] in {ids["u1"], ids["u2"]}


def test_复盘fake_provider时ready(seeded, monkeypatch) -> None:
    db, ids, tmp_path = seeded
    from rapport import config

    monkeypatch.setattr(config, "LLM_PROVIDER", "fake")
    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    r = client.post("/api/review", json={"scope": "conversation", "id": ids["cid"]})
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_brief_fake_provider时ready(seeded, monkeypatch) -> None:
    db, ids, tmp_path = seeded
    from rapport import config

    monkeypatch.setattr(config, "LLM_PROVIDER", "fake")
    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    r = client.get(f"/api/people/{ids['wang']}/brief")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_分析出错时返回error不500(seeded, monkeypatch) -> None:
    """provider 抛 AnalysisError → 端点 status:error，HTTP 仍 200。"""
    db, ids, tmp_path = seeded
    from rapport import config
    from rapport.analysis import AnalysisError

    class BoomProvider:
        def generate_json(self, system, user, schema):
            raise AnalysisError("模型调用失败（示例）")

    monkeypatch.setattr(config, "LLM_PROVIDER", "fake")
    # 让 get_provider 返回会爆炸的 provider
    monkeypatch.setattr(
        "rapport.web.app.get_provider", lambda: BoomProvider()
    )
    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    r = client.get(f"/api/people/{ids['wang']}/analysis")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["data"] is None
    assert "失败" in body["message"]
