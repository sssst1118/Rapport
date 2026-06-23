"""常驻引擎管线测试：假音频源 + 假转写器 + 假分离器 + 内存库 + 注入时钟。

全部不依赖真麦克风、真 whisper。覆盖：
- 两句话+中间静音 → 2 条 utterance 入当天 conversation、偏移正确对齐 day-WAV；
- 按天容器：同一天续写同一 conversation；跨午夜 → 新 conversation + 新 day-WAV；
- 状态：start/pause/resume/stop 写状态文件、暂停停止入库；
- 暂停后恢复：时间戳连续、不含暂停时段；
- 边界：全静音不产生空 utterance、stop 干净 finalize。
"""

from __future__ import annotations

import wave

import numpy as np

from rapport.alwayson.engine import Engine
from rapport.alwayson.status import read_status
from rapport.storage.db import Database
from rapport.transcribe.base import Segment

_SR = 16000


# ---- 假对象 --------------------------------------------------------------


class _假音频源:
    """可注入的假音频源：start(cb) 后由测试手动用 emit() 喂帧；不起线程。"""

    def __init__(self) -> None:
        self._cb = None
        self.started = False

    def start(self, callback) -> None:  # noqa: ANN001
        self._cb = callback
        self.started = True

    def emit(self, frame: np.ndarray) -> None:
        """测试驱动：把一帧交给引擎回调（模拟麦克风回调）。"""
        assert self._cb is not None
        self._cb(frame)

    def stop(self) -> None:
        self.started = False
        self._cb = None


class _按句转写器:
    """假转写器：对收到的音频片段，按其样本数估时长，回一句带文本的 Segment。

    文本用一个自增计数器区分，便于断言「第几句」。start/end 用 0 起算的片段内偏移，
    引擎应把它叠加到该句在 day-WAV 里的绝对偏移上（也可直接用片段长度，
    本测试只校验引擎是否把 day-WAV 绝对偏移写进库）。
    """

    def __init__(self) -> None:
        self.calls = 0
        self.received_durations_ms: list[int] = []

    def transcribe(self, audio_path: str) -> list[Segment]:
        self.calls += 1
        with wave.open(audio_path, "rb") as w:
            n = w.getnframes()
            sr = w.getframerate()
        dur_ms = int(round(n / sr * 1000))
        self.received_durations_ms.append(dur_ms)
        return [Segment(text=f"句{self.calls}", start_ms=0, end_ms=dur_ms)]


class _单人分离器:
    """假分离器：所有片段贴 'A'。"""

    def diarize(self, audio_path: str, segments: list[Segment]) -> list[Segment]:
        return [
            Segment(text=s.text, start_ms=s.start_ms, end_ms=s.end_ms, speaker_label="A")
            for s in segments
        ]


class _时钟:
    """可注入时钟：返回固定的 (date_str)；测试可推进到下一天。"""

    def __init__(self, day: str) -> None:
        self.day = day

    def today_str(self) -> str:
        return self.day


def _voiced(n: int, amp: float = 0.2) -> np.ndarray:
    return np.full(n, amp, dtype="float32")


def _silence(n: int) -> np.ndarray:
    return np.zeros(n, dtype="float32")


def _make_engine(tmp_path, db, *, clock, src):
    return Engine(
        db,
        transcriber=_按句转写器(),
        diarizer=_单人分离器(),
        audio_source=src,
        clock=clock,
        audio_dir=tmp_path / "audio",
        status_path=tmp_path / "recording_status.json",
        samplerate=_SR,
        silence_ms=700,
        min_utterance_s=0.5,
        max_utterance_s=30.0,
    )


# ---- 测试 ----------------------------------------------------------------


def test_两句话被切分入当天对话(tmp_path) -> None:
    db = Database()
    src = _假音频源()
    eng = _make_engine(tmp_path, db, clock=_时钟("2026-06-23"), src=src)
    try:
        eng.start()
        # 1s 有声 → 1s 静音 → 1s 有声 → 1s 静音
        src.emit(_voiced(_SR))
        src.emit(_silence(_SR))
        src.emit(_voiced(_SR))
        src.emit(_silence(_SR))
        eng.stop()

        convs = db.list_conversations()
        assert len(convs) == 1
        cid = convs[0]["id"]
        rows = db.get_utterances(cid)
        assert [r["text"] for r in rows] == ["句1", "句2"]
        assert [r["speaker_label"] for r in rows] == ["A", "A"]
        # 第一句从 day-WAV 0ms 起，第二句在第一段静音之后
        assert rows[0]["start_ms"] == 0
        assert rows[1]["start_ms"] > rows[0]["end_ms"]
    finally:
        db.close()


def test_day_wav_落盘且utterance偏移对齐(tmp_path) -> None:
    db = Database()
    src = _假音频源()
    eng = _make_engine(tmp_path, db, clock=_时钟("2026-06-23"), src=src)
    try:
        eng.start()
        src.emit(_voiced(_SR))
        src.emit(_silence(_SR))
        eng.stop()

        cid = db.list_conversations()[0]["id"]
        conv = db.get_conversation(cid)
        wav_path = tmp_path / "audio" / "2026-06-23.wav"
        assert wav_path.is_file()
        # conversation.audio_path 指向当天 day-WAV（用于 /api/.../audio 回放）
        assert conv["audio_path"].endswith("2026-06-23.wav")
        # day-WAV 至少含写入的有声+静音样本
        with wave.open(str(wav_path), "rb") as w:
            assert w.getnframes() >= _SR
        rows = db.get_utterances(cid)
        u = rows[0]
        # start_ms/end_ms 落在 day-WAV 时长范围内
        with wave.open(str(wav_path), "rb") as w:
            total_ms = int(w.getnframes() / w.getframerate() * 1000)
        assert 0 <= u["start_ms"] < u["end_ms"] <= total_ms
    finally:
        db.close()


def test_同一天重启续写同一对话(tmp_path) -> None:
    clock = _时钟("2026-06-23")
    db = Database()
    try:
        # 第一次会话
        src1 = _假音频源()
        eng1 = _make_engine(tmp_path, db, clock=clock, src=src1)
        eng1.start()
        src1.emit(_voiced(_SR))
        src1.emit(_silence(_SR))
        eng1.stop()
        cid1 = db.list_conversations()[0]["id"]

        # 守护进程重启（同一天）：应续写同一个 conversation
        src2 = _假音频源()
        eng2 = _make_engine(tmp_path, db, clock=clock, src=src2)
        eng2.start()
        src2.emit(_voiced(_SR))
        src2.emit(_silence(_SR))
        eng2.stop()

        convs = db.list_conversations()
        assert len(convs) == 1  # 仍只有一个当天对话
        rows = db.get_utterances(cid1)
        assert len(rows) == 2  # 两次会话各一句
        # 续写的第二句偏移应接在第一句之后（day-WAV 末尾续写）
        assert rows[1]["start_ms"] > rows[0]["end_ms"]
    finally:
        db.close()


def test_跨午夜开新对话与新day_wav(tmp_path) -> None:
    clock = _时钟("2026-06-23")
    db = Database()
    src = _假音频源()
    eng = _make_engine(tmp_path, db, clock=clock, src=src)
    try:
        eng.start()
        src.emit(_voiced(_SR))
        src.emit(_silence(_SR))
        # 跨午夜：时钟推进到新一天
        clock.day = "2026-06-24"
        src.emit(_voiced(_SR))
        src.emit(_silence(_SR))
        eng.stop()

        convs = db.list_conversations()
        assert len(convs) == 2
        notes = sorted((c["note"] or "") for c in convs)
        assert any("2026-06-23" in n for n in notes)
        assert any("2026-06-24" in n for n in notes)
        # 两个 day-WAV 都落了盘
        assert (tmp_path / "audio" / "2026-06-23.wav").is_file()
        assert (tmp_path / "audio" / "2026-06-24.wav").is_file()
    finally:
        db.close()


def test_状态文件随生命周期变化(tmp_path) -> None:
    db = Database()
    src = _假音频源()
    status_path = tmp_path / "recording_status.json"
    eng = _make_engine(tmp_path, db, clock=_时钟("2026-06-23"), src=src)
    try:
        assert read_status(status_path) == {"recording": False, "paused": False}
        eng.start()
        assert read_status(status_path) == {"recording": True, "paused": False}
        eng.pause()
        assert read_status(status_path) == {"recording": True, "paused": True}
        eng.resume()
        assert read_status(status_path) == {"recording": True, "paused": False}
        eng.stop()
        # stop 后状态文件被清，诚实回未录音
        assert read_status(status_path) == {"recording": False, "paused": False}
    finally:
        db.close()


def test_暂停期间不入库(tmp_path) -> None:
    db = Database()
    src = _假音频源()
    eng = _make_engine(tmp_path, db, clock=_时钟("2026-06-23"), src=src)
    try:
        eng.start()
        eng.pause()
        # 暂停时喂一堆有声/静音都不该入库
        src.emit(_voiced(_SR))
        src.emit(_silence(_SR))
        src.emit(_voiced(_SR))
        src.emit(_silence(_SR))
        eng.resume()
        eng.stop()
        convs = db.list_conversations()
        if convs:
            cid = convs[0]["id"]
            assert db.get_utterances(cid) == []
    finally:
        db.close()


def test_暂停恢复时间戳连续不含暂停时段(tmp_path) -> None:
    db = Database()
    src = _假音频源()
    eng = _make_engine(tmp_path, db, clock=_时钟("2026-06-23"), src=src)
    try:
        eng.start()
        # 第一句
        src.emit(_voiced(_SR))
        src.emit(_silence(_SR))
        # 暂停期间喂大量音频（应被完全丢弃，不进 day-WAV、不计入时间）
        eng.pause()
        src.emit(_voiced(5 * _SR))
        eng.resume()
        # 第二句
        src.emit(_voiced(_SR))
        src.emit(_silence(_SR))
        eng.stop()

        cid = db.list_conversations()[0]["id"]
        rows = db.get_utterances(cid)
        assert len(rows) == 2
        # 第二句紧接第一句（中间只隔一段静音的 day-WAV 长度），
        # 绝不包含暂停期间那 5s——否则 start_ms 会暴涨到 >7000ms
        gap = rows[1]["start_ms"] - rows[0]["end_ms"]
        assert gap < 2000  # 只隔约 1s 静音，远小于暂停的 5s

        # day-WAV 时长也不该包含暂停的 5s
        wav_path = tmp_path / "audio" / "2026-06-23.wav"
        with wave.open(str(wav_path), "rb") as w:
            total_ms = int(w.getnframes() / w.getframerate() * 1000)
        assert total_ms < 6000  # 约 4s（两句各1s+两段静音各1s），远小于含暂停的 9s
    finally:
        db.close()


def test_全静音不产生空utterance(tmp_path) -> None:
    db = Database()
    src = _假音频源()
    eng = _make_engine(tmp_path, db, clock=_时钟("2026-06-23"), src=src)
    try:
        eng.start()
        src.emit(_silence(3 * _SR))
        eng.stop()
        convs = db.list_conversations()
        if convs:
            assert db.get_utterances(convs[0]["id"]) == []
    finally:
        db.close()


def test_stop后再stop不抛错(tmp_path) -> None:
    db = Database()
    src = _假音频源()
    eng = _make_engine(tmp_path, db, clock=_时钟("2026-06-23"), src=src)
    try:
        eng.start()
        src.emit(_voiced(_SR))
        src.emit(_silence(_SR))
        eng.stop()
        eng.stop()  # 幂等
    finally:
        db.close()
