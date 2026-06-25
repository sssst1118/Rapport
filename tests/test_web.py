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

    # 显式隔离 status_path 到 tmp（不存在→默认未录音），否则 /api/status 会读真实的
    # data/recording_status.json——本机跑过 always-on 后它可能残留 recording:true，
    # 让 test_状态诚实显示未录音 在干净代码上也偶发变红（测试隔离脆弱性）。
    app = create_app(
        db_path=tmp_path / "rapport.db",
        repo_root=tmp_path,
        status_path=tmp_path / "recording_status.json",
    )
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


def test_状态读守护进程写的状态文件(tmp_path) -> None:
    """/api/status 应读状态文件：守护进程写 recording=True → 端点变真。"""
    from rapport.alwayson.status import write_status

    status_path = tmp_path / "recording_status.json"
    write_status(status_path, recording=True, paused=True)
    app = create_app(db_path=tmp_path / "rapport.db", status_path=status_path)
    client = TestClient(app)
    r = client.get("/api/status")
    assert r.status_code == 200
    assert r.json() == {"recording": True, "paused": True}


def test_状态文件缺失或损坏不报500(tmp_path) -> None:
    """状态文件不存在/损坏时 /api/status 诚实回未录音、绝不抛 500。"""
    status_path = tmp_path / "recording_status.json"
    status_path.write_text("{ broken", encoding="utf-8")
    app = create_app(db_path=tmp_path / "rapport.db", status_path=status_path)
    client = TestClient(app)
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


# ---- 设置页端点（M5.5 Task 3）：读写语言模型配置，落 config.json ---------
#
# 这组端点与 db 数据无关，只读写 data_root()/config.json。测试统一把
# _frozen.data_root() monkeypatch 到 tmp_path，于是 save_config / _load_config_file /
# anthropic_api_key 全部落在 tmp，绝不污染真用户配置；并清掉相关环境变量，
# 让「有效值」由 config.json（或默认）决定，断言可控。


@pytest.fixture
def settings_client(tmp_path, monkeypatch):
    """把配置层 data_root 指向 tmp，并清环境变量，返回一个最小 app 的 TestClient。

    config.py 内部经 ``_frozen.data_root()`` 定位 config.json，monkeypatch 它即可把
    读写都关进 tmp。清掉 RAPPORT_LLM_PROVIDER/RAPPORT_LLM_MODEL/ANTHROPIC_API_KEY，
    避免宿主环境串味（否则 env_overrides 会非空、有效值被环境盖掉）。
    """
    from rapport import _frozen

    monkeypatch.setattr(_frozen, "data_root", lambda: tmp_path)
    monkeypatch.delenv("RAPPORT_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("RAPPORT_LLM_MODEL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("RAPPORT_WHISPER_MODEL", raising=False)
    monkeypatch.delenv("RAPPORT_WHISPER_DEVICE", raising=False)

    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    yield client, tmp_path
    # config.json 落在 tmp_path，随 tmp 夹具自动清理，无需手动删。


def test_设置默认未配置时回显none且无key(settings_client) -> None:
    """无 config.json、无环境变量：provider=none、默认模型、has_api_key=false、无覆盖。"""
    client, _ = settings_client
    r = client.get("/api/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["llm_provider"] == "none"
    assert body["llm_model"] == "claude-opus-4-8"  # config.LLM_MODEL 默认
    assert body["has_api_key"] is False
    assert body["env_overrides"] == []
    # 语音转写默认值（config 默认 base / cpu）
    assert body["whisper_model"] == "base"
    assert body["whisper_device"] == "cpu"
    # 绝不回显明文 key：响应里不应出现任何 *_api_key 字段
    assert "anthropic_api_key" not in body
    assert "api_key" not in body


def test_保存设置后GET反映持久化(settings_client) -> None:
    """POST 改 provider/model 后，GET 立即反映（写进 config.json、热读）。"""
    client, root = settings_client
    r = client.post(
        "/api/settings",
        json={"llm_provider": "ollama", "llm_model": "qwen2.5:7b-instruct"},
    )
    assert r.status_code == 200
    # POST 返回与 GET 同款结构
    assert r.json()["llm_provider"] == "ollama"
    assert r.json()["llm_model"] == "qwen2.5:7b-instruct"
    # 再 GET 确认持久化
    g = client.get("/api/settings").json()
    assert g["llm_provider"] == "ollama"
    assert g["llm_model"] == "qwen2.5:7b-instruct"
    # 确实写进了 config.json 文件
    import json

    saved = json.loads((root / "config.json").read_text(encoding="utf-8"))
    assert saved["llm_provider"] == "ollama"
    assert saved["llm_model"] == "qwen2.5:7b-instruct"


def test_保存anthropic_key后has_api_key为真但不回显明文(settings_client) -> None:
    """带 key 保存后 has_api_key=true；GET/POST 响应都不回显明文 key。"""
    client, root = settings_client
    r = client.post(
        "/api/settings",
        json={
            "llm_provider": "anthropic",
            "llm_model": "claude-opus-4-8",
            "anthropic_api_key": "sk-ant-secret-xyz",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["llm_provider"] == "anthropic"
    assert body["has_api_key"] is True
    # 响应体里绝不出现明文 key
    assert "sk-ant-secret-xyz" not in r.text
    # GET 同样不回显
    g = client.get("/api/settings")
    assert g.json()["has_api_key"] is True
    assert "sk-ant-secret-xyz" not in g.text


def test_空key不覆盖已存key(settings_client) -> None:
    """先存 key，再发空串/省略 key 的保存：已存的 key 不被清掉。"""
    client, root = settings_client
    # 先存一个 key
    client.post(
        "/api/settings",
        json={"llm_provider": "anthropic", "anthropic_api_key": "sk-ant-keep-me"},
    )
    # 空串 key 的保存（只改 model）
    r = client.post(
        "/api/settings",
        json={
            "llm_provider": "anthropic",
            "llm_model": "claude-haiku-4-5",
            "anthropic_api_key": "",
        },
    )
    assert r.status_code == 200
    assert r.json()["has_api_key"] is True  # 仍在
    # config.json 里的 key 仍是原值，未被空串覆盖
    import json

    saved = json.loads((root / "config.json").read_text(encoding="utf-8"))
    assert saved["anthropic_api_key"] == "sk-ant-keep-me"
    assert saved["llm_model"] == "claude-haiku-4-5"  # model 确实更新了

    # 完全省略 key 字段的保存：同样不覆盖
    r2 = client.post(
        "/api/settings", json={"llm_provider": "anthropic", "llm_model": "x"}
    )
    assert r2.status_code == 200
    assert r2.json()["has_api_key"] is True
    saved2 = json.loads((root / "config.json").read_text(encoding="utf-8"))
    assert saved2["anthropic_api_key"] == "sk-ant-keep-me"


def test_环境变量覆盖时env_overrides列出且回显有效值(tmp_path, monkeypatch) -> None:
    """环境变量设了 provider/key：env_overrides 列出对应项，有效值取环境值。"""
    from rapport import _frozen

    monkeypatch.setattr(_frozen, "data_root", lambda: tmp_path)
    # config.json 里写 ollama，但环境变量把 provider 顶成 anthropic
    monkeypatch.setenv("RAPPORT_LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("RAPPORT_LLM_MODEL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")

    from rapport import config

    config.save_config({"llm_provider": "ollama"})

    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    body = client.get("/api/settings").json()
    # 有效值取环境（env > file）
    assert body["llm_provider"] == "anthropic"
    assert body["has_api_key"] is True
    # provider 与 key 都被环境覆盖，model 没有
    assert "llm_provider" in body["env_overrides"]
    assert "anthropic_api_key" in body["env_overrides"]
    assert "llm_model" not in body["env_overrides"]
    # 明文 env key 也不回显
    assert "sk-ant-from-env" not in client.get("/api/settings").text


def test_坏输入不报500给4xx(settings_client) -> None:
    """provider 取非法值（不在 none/ollama/anthropic）→ 422，不 500。"""
    client, _ = settings_client
    r = client.post("/api/settings", json={"llm_provider": "gpt-9000"})
    assert r.status_code == 422  # pydantic 校验失败
    # 不允许的取值不应落库
    g = client.get("/api/settings").json()
    assert g["llm_provider"] == "none"


def test_保存whisper设置后GET反映并落config_json(settings_client) -> None:
    """POST 改 whisper_model/device 后，GET 立即反映且写进 config.json。"""
    client, root = settings_client
    r = client.post(
        "/api/settings",
        json={"whisper_model": "small", "whisper_device": "cuda"},
    )
    assert r.status_code == 200
    assert r.json()["whisper_model"] == "small"
    assert r.json()["whisper_device"] == "cuda"
    # 再 GET 确认持久化
    g = client.get("/api/settings").json()
    assert g["whisper_model"] == "small"
    assert g["whisper_device"] == "cuda"
    # 确实写进了 config.json
    import json

    saved = json.loads((root / "config.json").read_text(encoding="utf-8"))
    assert saved["whisper_model"] == "small"
    assert saved["whisper_device"] == "cuda"


def test_只改whisper不动已存llm设置(settings_client) -> None:
    """只 POST whisper 字段时，已存的 llm 设置与 key 不被清空。"""
    client, root = settings_client
    client.post(
        "/api/settings",
        json={"llm_provider": "anthropic", "anthropic_api_key": "sk-ant-keep"},
    )
    r = client.post("/api/settings", json={"whisper_model": "medium"})
    assert r.status_code == 200
    body = r.json()
    assert body["whisper_model"] == "medium"
    assert body["llm_provider"] == "anthropic"  # 未被动
    assert body["has_api_key"] is True  # key 仍在

    import json

    saved = json.loads((root / "config.json").read_text(encoding="utf-8"))
    assert saved["anthropic_api_key"] == "sk-ant-keep"
    assert saved["whisper_model"] == "medium"


def test_whisper坏取值不报500给4xx(settings_client) -> None:
    """whisper_model/device 取非法值 → 422，不 500，且不落库。"""
    client, _ = settings_client
    r = client.post("/api/settings", json={"whisper_model": "gpt-whisper"})
    assert r.status_code == 422
    r2 = client.post("/api/settings", json={"whisper_device": "tpu"})
    assert r2.status_code == 422
    g = client.get("/api/settings").json()
    assert g["whisper_model"] == "base"  # 默认未变
    assert g["whisper_device"] == "cpu"


def test_whisper环境变量覆盖时env_overrides列出(tmp_path, monkeypatch) -> None:
    """env 设了 whisper_model/device：env_overrides 列出且有效值取环境。"""
    from rapport import _frozen

    monkeypatch.setattr(_frozen, "data_root", lambda: tmp_path)
    monkeypatch.setenv("RAPPORT_WHISPER_MODEL", "large-v3")
    monkeypatch.setenv("RAPPORT_WHISPER_DEVICE", "cuda")

    app = create_app(db_path=tmp_path / "rapport.db", repo_root=tmp_path)
    client = TestClient(app)
    body = client.get("/api/settings").json()
    assert body["whisper_model"] == "large-v3"
    assert body["whisper_device"] == "cuda"
    assert "whisper_model" in body["env_overrides"]
    assert "whisper_device" in body["env_overrides"]


# ---- 静态托管降级 -------------------------------------------------------


def test_前端未构建时根路径友好提示(seeded) -> None:
    client, _, _ = seeded
    r = client.get("/")
    # frontend/dist 不存在（测试用 tmp_path 作仓库根），应给出友好提示而非崩溃
    assert r.status_code == 200
    assert "构建" in r.text or "build" in r.text.lower()
