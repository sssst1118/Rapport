"""day-WAV 增量追加 + WAV 头长度字段更新测试（最易错处，仔细验）。

不依赖任何硬件：直接造 numpy float32 样本，追加写盘，再用标准 wave 模块读回，
断言帧数/时长/声道/位深正确——这等价于 /api/conversations/{id}/audio 用 Range
能正确流式播放（它读的就是同一个 WAV 文件的字节区间，前提是头长度字段诚实）。
"""

from __future__ import annotations

import struct
import wave

import numpy as np

from rapport.alwayson.daywav import DayWavWriter

_SR = 16000


def _read_wav(path) -> tuple[int, int, int, int]:
    """读回 WAV，返回 (声道, 位深字节, 采样率, 帧数)。"""
    with wave.open(str(path), "rb") as w:
        return (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes())


def test_新建空day_wav头合法且零帧(tmp_path) -> None:
    path = tmp_path / "2026-06-23.wav"
    w = DayWavWriter(path, samplerate=_SR)
    try:
        assert path.is_file()
        ch, sw, sr, n = _read_wav(path)
        assert (ch, sw, sr, n) == (1, 2, _SR, 0)
    finally:
        w.close()


def test_追加一批样本帧数正确(tmp_path) -> None:
    path = tmp_path / "day.wav"
    w = DayWavWriter(path, samplerate=_SR)
    try:
        w.append(np.zeros(_SR, dtype="float32"))  # 1s
        ch, sw, sr, n = _read_wav(path)
        assert n == _SR
    finally:
        w.close()


def test_追加两批帧数与时长累加且头长度字段正确(tmp_path) -> None:
    path = tmp_path / "day.wav"
    w = DayWavWriter(path, samplerate=_SR)
    try:
        w.append(np.zeros(_SR, dtype="float32"))  # 1s
        w.append(np.zeros(2 * _SR, dtype="float32"))  # 2s
        ch, sw, sr, n = _read_wav(path)
        assert n == 3 * _SR  # 共 3s

        # 直接核对 RIFF ChunkSize(偏移4) 与 data Subchunk2Size(偏移40) 字段
        raw = path.read_bytes()
        data_bytes = 3 * _SR * 2  # 16-bit 单声道
        riff_size = struct.unpack_from("<I", raw, 4)[0]
        data_size = struct.unpack_from("<I", raw, 40)[0]
        assert data_size == data_bytes
        assert riff_size == 36 + data_bytes  # 标准 44 字节头：4..文件尾
        # 文件总长 = 44 字节头 + data
        assert len(raw) == 44 + data_bytes
    finally:
        w.close()


def test_total_samples_随追加递增(tmp_path) -> None:
    path = tmp_path / "day.wav"
    w = DayWavWriter(path, samplerate=_SR)
    try:
        assert w.total_samples == 0
        w.append(np.zeros(100, dtype="float32"))
        assert w.total_samples == 100
        w.append(np.zeros(50, dtype="float32"))
        assert w.total_samples == 150
    finally:
        w.close()


def test_float样本被转成int16无溢出(tmp_path) -> None:
    path = tmp_path / "day.wav"
    w = DayWavWriter(path, samplerate=_SR)
    try:
        # 含越界值，应被裁剪而非回绕
        frame = np.array([0.0, 1.0, -1.0, 2.0, -2.0, 0.5], dtype="float32")
        w.append(frame)
    finally:
        w.close()
    with wave.open(str(path), "rb") as r:
        data = r.readframes(r.getnframes())
    vals = struct.unpack("<6h", data)
    assert vals[0] == 0
    assert vals[1] == 32767  # 1.0 → 满幅
    assert vals[2] == -32768  # -1.0
    assert vals[3] == 32767  # 2.0 裁剪到满幅，不回绕
    assert vals[4] == -32768  # -2.0 裁剪
    assert abs(vals[5] - 16383) <= 1  # 0.5 ≈ 半幅


def test_重开已存在day_wav续写末尾(tmp_path) -> None:
    path = tmp_path / "day.wav"
    w1 = DayWavWriter(path, samplerate=_SR)
    w1.append(np.zeros(_SR, dtype="float32"))
    w1.close()

    # 守护进程重启：对同一天的 WAV 续写，应接在末尾、不清空
    w2 = DayWavWriter(path, samplerate=_SR)
    try:
        assert w2.total_samples == _SR  # 续上已有 1s
        w2.append(np.zeros(_SR, dtype="float32"))
        ch, sw, sr, n = _read_wav(path)
        assert n == 2 * _SR
    finally:
        w2.close()
