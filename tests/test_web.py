"""FastAPI 后端测试：状态、人物、对话、改写、解读占位、音频 Range。

全部跑在内存库（:memory:）上注入 app，无需任何重依赖。
风格对齐 tests/test_db.py：中文测试名、纯逻辑、FastAPI TestClient。
"""

from __future__ import annotations

import struct
import wave

import pytest
from fastapi.testclient import TestClient

from rapport.storage.db import Database
from rapport.web import create_app


def _make_wav(path, n_frames: int = 8000) -> None:
    """造一个最小的单声道 16bit WAV，供音频 Range 测试用。"""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(struct.pack("<" + "h" * n_frames, *([0] * n_frames)))


@pytest.fixture
def seeded(tmp_path):
    """造一个有人物、对话、话语、标注的文件库，并返回 (TestClient, db, 关键 id)。

    用文件库（而非 :memory:）是因为 web 层把数据库连接封闭到一个专属工作线程，
    测试线程这边用自己的 Database 句柄读同一个文件做断言；两端通过同一文件协作。
    """
    db = Database(tmp_path / "rapport.db")
    # 人
    wo = db.add_person("我", relation="自己")
    wang = db.add_person("老王", relation="同事")
    li = db.add_person("小李", relation="实习生")
    # 一段有音频的对话
    wav = tmp_path / "sample.wav"
    _make_wav(wav)
    cid = db.add_conversation(audio_path="sample.wav", note="午饭闲聊")
    u1 = db.add_utterance(
        cid, text="你好啊老王", speaker_label="A", person_id=wo, start_ms=0, end_ms=500
    )
    u2 = db.add_utterance(
        cid, text="最近项目怎么样", speaker_label="B", person_id=wang,
        start_ms=500, end_ms=1200,
    )
    # 同一说话人标签 A 的第二句，未归属（用于 relabel）
    u3 = db.add_utterance(
        cid, text="还得再确认一下", speaker_label="A", start_ms=1200, end_ms=1800
    )
    db.add_annotation(u1, type="tag", value="重要")
    # 第二段对话：小李参与，无音频
    cid2 = db.add_conversation(note="散步")
    db.add_utterance(cid2, text="实习还顺利吗", speaker_label="A", person_id=li)

    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    ids = {
        "wo": wo, "wang": wang, "li": li,
        "cid": cid, "cid2": cid2,
        "u1": u1, "u2": u2, "u3": u3,
    }
    yield client, db, ids
    db.close()


# ---- 状态 ----------------------------------------------------------------


def test_状态诚实显示未录音(seeded) -> None:
    client, _, _ = seeded
    r = client.get("/api/status")
    assert r.status_code == 200
    assert r.json() == {"recording": False, "paused": False}


# ---- 人物 ----------------------------------------------------------------


def test_人物列表含话语数(seeded) -> None:
    client, _, ids = seeded
    r = client.get("/api/people")
    assert r.status_code == 200
    people = r.json()
    by_id = {p["id"]: p for p in people}
    assert by_id[ids["wang"]]["name"] == "老王"
    assert by_id[ids["wang"]]["utterance_count"] == 1
    assert by_id[ids["wo"]]["utterance_count"] == 1
    # 字段齐全
    assert set(people[0]) >= {"id", "name", "avatar", "relation", "utterance_count"}


def test_新建人物(seeded) -> None:
    client, db, _ = seeded
    r = client.post("/api/people", json={"name": "陈夕", "relation": "朋友"})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "陈夕"
    assert body["relation"] == "朋友"
    assert "id" in body and "avatar" in body
    # 确实落库
    assert db.get_person(body["id"])["name"] == "陈夕"


def test_人物详情含对话数与话语数(seeded) -> None:
    client, _, ids = seeded
    r = client.get(f"/api/people/{ids['wo']}")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "我"
    assert body["utterance_count"] == 1
    assert body["conversation_count"] == 1
    assert {"created_at", "updated_at"} <= set(body)


def test_人物详情缺失404(seeded) -> None:
    client, _, _ = seeded
    assert client.get("/api/people/99999").status_code == 404


def test_人物的话语跨对话最近优先(seeded) -> None:
    client, _, ids = seeded
    r = client.get(f"/api/people/{ids['wang']}/utterances")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["text"] == "最近项目怎么样"
    assert rows[0]["conversation_note"] == "午饭闲聊"
    assert {"id", "conversation_id", "started_at", "speaker_label",
            "start_ms", "end_ms"} <= set(rows[0])


# ---- 对话 ----------------------------------------------------------------


def test_对话列表最近优先含参与者(seeded) -> None:
    client, _, ids = seeded
    r = client.get("/api/conversations")
    assert r.status_code == 200
    convs = r.json()
    by_id = {c["id"]: c for c in convs}
    c1 = by_id[ids["cid"]]
    assert c1["note"] == "午饭闲聊"
    assert c1["has_audio"] is True
    assert c1["utterance_count"] == 3
    names = {p["name"] for p in c1["participants"]}
    assert names == {"我", "老王"}
    # 第二段无音频
    assert by_id[ids["cid2"]]["has_audio"] is False


def test_对话详情含话语与标注与去重说话人(seeded) -> None:
    client, _, ids = seeded
    r = client.get(f"/api/conversations/{ids['cid']}")
    assert r.status_code == 200
    body = r.json()
    assert body["note"] == "午饭闲聊"
    assert body["has_audio"] is True
    assert sorted(body["speakers"]) == ["A", "B"]
    assert len(body["utterances"]) == 3
    first = body["utterances"][0]
    assert first["text"] == "你好啊老王"
    assert first["annotations"][0]["type"] == "tag"
    assert first["annotations"][0]["value"] == "重要"
    names = {p["name"] for p in body["participants"]}
    assert names == {"我", "老王"}


def test_对话详情缺失404(seeded) -> None:
    client, _, _ = seeded
    assert client.get("/api/conversations/99999").status_code == 404


# ---- 音频 Range ----------------------------------------------------------


def test_音频不带Range返回全量(seeded) -> None:
    client, _, ids = seeded
    r = client.get(f"/api/conversations/{ids['cid']}/audio")
    assert r.status_code == 200
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-type"] == "audio/wav"


def test_音频带Range返回206与ContentRange(seeded) -> None:
    client, _, ids = seeded
    r = client.get(
        f"/api/conversations/{ids['cid']}/audio",
        headers={"Range": "bytes=0-1023"},
    )
    assert r.status_code == 206
    assert r.headers["content-range"].startswith("bytes 0-1023/")
    assert int(r.headers["content-length"]) == 1024
    assert len(r.content) == 1024


def test_音频缺失对话404(seeded) -> None:
    client, _, ids = seeded
    # 第二段对话没有音频
    assert client.get(f"/api/conversations/{ids['cid2']}/audio").status_code == 404


# ---- 改写 ----------------------------------------------------------------


def test_改话语文字(seeded) -> None:
    client, db, ids = seeded
    r = client.patch(f"/api/utterances/{ids['u1']}", json={"text": "你好老王今天忙吗"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    rows = db.get_utterances(ids["cid"])
    assert rows[0]["text"] == "你好老王今天忙吗"


def test_改话语归属(seeded) -> None:
    client, db, ids = seeded
    r = client.patch(
        f"/api/utterances/{ids['u3']}/person", json={"person_id": ids["wang"]}
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    texts = [x["text"] for x in db.get_utterances_for_person(ids["wang"])]
    assert "还得再确认一下" in texts


def test_改话语归属可置空(seeded) -> None:
    client, db, ids = seeded
    r = client.patch(
        f"/api/utterances/{ids['u2']}/person", json={"person_id": None}
    )
    assert r.status_code == 200
    assert db.get_utterances_for_person(ids["wang"]) == []


def test_整段说话人快速映射返回条数(seeded) -> None:
    client, db, ids = seeded
    # 把对话内标签 A 的全部话语归到老王（共 2 句：u1、u3）
    r = client.post(
        f"/api/conversations/{ids['cid']}/relabel",
        json={"speaker_label": "A", "person_id": ids["wang"]},
    )
    assert r.status_code == 200
    assert r.json() == {"updated": 2}


def test_加标注与删标注(seeded) -> None:
    client, db, ids = seeded
    r = client.post(
        f"/api/utterances/{ids['u2']}/annotations",
        json={"type": "note", "value": "这里他有点犹豫"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "note"
    assert body["value"] == "这里他有点犹豫"
    aid = body["id"]
    assert any(a["id"] == aid for a in db.get_annotations(ids["u2"]))
    # 删除
    r2 = client.delete(f"/api/annotations/{aid}")
    assert r2.status_code == 200
    assert r2.json() == {"ok": True}
    assert all(a["id"] != aid for a in db.get_annotations(ids["u2"]))


# ---- 解读信封（M4）：默认未配置 provider → needs_setup -------------------
#
# M4 已把这 5 个解读端点接到按需分析。seeded 夹具不设 RAPPORT_LLM_PROVIDER，
# 默认 none（未配置），故统一返回 needs_setup 信封（仍 200、data 为 None）。
# ready / error 两态由 tests/test_analysis.py 用 fake provider 覆盖。


def _assert_needs_setup(body) -> None:
    assert body["kind"] == "interpretation"
    assert body["status"] == "needs_setup"
    assert body["data"] is None
    assert isinstance(body["message"], str) and body["message"]


def test_对话摘要未配置时needs_setup(seeded) -> None:
    client, _, ids = seeded
    r = client.get(f"/api/conversations/{ids['cid']}/summary")
    assert r.status_code == 200
    _assert_needs_setup(r.json())


def test_人物分析未配置时needs_setup(seeded) -> None:
    client, _, ids = seeded
    r = client.get(f"/api/people/{ids['wang']}/analysis")
    assert r.status_code == 200
    _assert_needs_setup(r.json())


def test_见面前brief未配置时needs_setup(seeded) -> None:
    client, _, ids = seeded
    r = client.get(f"/api/people/{ids['wang']}/brief")
    assert r.status_code == 200
    _assert_needs_setup(r.json())


def test_划选分析未配置时needs_setup(seeded) -> None:
    client, _, ids = seeded
    r = client.post("/api/analyze", json={"utterance_ids": [ids["u1"], ids["u2"]]})
    assert r.status_code == 200
    _assert_needs_setup(r.json())


# ---- 静态托管降级 -------------------------------------------------------


def test_前端未构建时根路径友好提示(seeded) -> None:
    client, _, _ = seeded
    r = client.get("/")
    # frontend/dist 不存在（测试用 tmp_path 作仓库根），应给出友好提示而非崩溃
    assert r.status_code == 200
    assert "构建" in r.text or "build" in r.text.lower()
