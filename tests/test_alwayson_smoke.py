"""冒烟：假源驱动 Engine 跑通整链，且产出的 day-WAV 能被 web 音频端点 Range 播放。

不开真麦、不用真 whisper：假源喂两句话，Engine 落库 + 写 day-WAV，
再用 FastAPI TestClient 对当天 conversation 发 Range 请求，验证 206 + 字节正确。
这等价于前端 🔊 跳播读 day-WAV 的真实路径。
"""

from __future__ import annotations

import wave

import numpy as np
from fastapi.testclient import TestClient

from rapport.alwayson.engine import Engine
from rapport.storage.db import Database
from rapport.transcribe.base import Segment
from rapport.web import create_app

_SR = 16000


class _源:
    def __init__(self) -> None:
        self._cb = None

    def start(self, callback) -> None:  # noqa: ANN001
        self._cb = callback

    def emit(self, f) -> None:  # noqa: ANN001
        self._cb(f)

    def stop(self) -> None:
        self._cb = None


class _转写器:
    def transcribe(self, audio_path: str) -> list[Segment]:
        with wave.open(audio_path, "rb") as w:
            dur = int(w.getnframes() / w.getframerate() * 1000)
        return [Segment(text="一句真转写", start_ms=0, end_ms=dur)]


class _分离器:
    def diarize(self, audio_path: str, segments):  # noqa: ANN001
        return [
            Segment(text=s.text, start_ms=s.start_ms, end_ms=s.end_ms, speaker_label="A")
            for s in segments
        ]


class _时钟:
    def today_str(self) -> str:
        return "2026-06-23"


def test_整链冒烟_daywav可被Range播放(tmp_path) -> None:
    db_path = tmp_path / "rapport.db"
    audio_dir = tmp_path / "audio"

    db = Database(db_path)
    src = _源()
    eng = Engine(
        db,
        transcriber=_转写器(),
        diarizer=_分离器(),
        audio_source=src,
        clock=_时钟(),
        audio_dir=audio_dir,
        status_path=tmp_path / "status.json",
        samplerate=_SR,
        min_utterance_s=0.5,
        repo_root=tmp_path,  # 让写库 audio_path 相对 tmp_path，web 用同基准解析
    )
    eng.start()
    src.emit(np.full(_SR, 0.2, dtype="float32"))
    src.emit(np.zeros(_SR, dtype="float32"))
    eng.stop()

    cid = db.list_conversations()[0]["id"]
    assert len(db.get_utterances(cid)) == 1
    db.close()

    # web 端点用同一个文件库 + 同一个 repo_root 解析 day-WAV，发 Range 请求
    app = create_app(db_path=db_path, repo_root=tmp_path)
    client = TestClient(app)
    r = client.get(f"/api/conversations/{cid}/audio", headers={"Range": "bytes=0-43"})
    assert r.status_code == 206
    assert r.content[:4] == b"RIFF"  # 头 44 字节合法 RIFF
    # 无 Range 全量也能取
    r2 = client.get(f"/api/conversations/{cid}/audio")
    assert r2.status_code == 200
    assert r2.headers.get("accept-ranges") == "bytes"
