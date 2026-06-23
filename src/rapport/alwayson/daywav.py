"""day-WAV 追加写：按天滚动的一个 WAV 文件，支持增量追加 + 头长度字段更新。

为什么不直接用 Python `wave` 模块写：`wave` 在 close 时才回填头长度，长驻追加
过程中文件头里的长度字段是「写一半」的状态，会让正在播放的 `/api/.../audio`
（按 file size + Range 读字节）拿到错误时长甚至坏头。这里改为：

1. 建文件时先写好标准 44 字节 PCM WAV 头（16-bit 单声道）；
2. 每次 append 把 float32 样本裁剪并转 int16，**直接 seek 到文件尾 append**；
3. append 后 **seek 回偏移 4 改 RIFF ChunkSize、偏移 40 改 data Subchunk2Size**，
   并 flush——任何时刻文件都是一个长度字段诚实、可被 Range 正确切片播放的合法 WAV。

16-bit 单声道与现有 recorder（soundfile 默认 PCM_16 单声道）一致，
前端 🔊 跳播读到的就是同一种格式。
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

from .. import config

# 标准 PCM WAV 头长度（RIFF 12 + fmt 24 + data 头 8）。
_HEADER_SIZE = 44
_SAMPWIDTH = 2  # 16-bit PCM
_CHANNELS = 1  # 单声道


def _build_header(samplerate: int, data_bytes: int) -> bytes:
    """构造 44 字节标准 PCM WAV 头（16-bit 单声道）。

    Args:
        samplerate: 采样率（Hz）。
        data_bytes: data 块的字节数（= 样本数 * 2）。

    Returns:
        44 字节头。
    """
    byte_rate = samplerate * _CHANNELS * _SAMPWIDTH
    block_align = _CHANNELS * _SAMPWIDTH
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_bytes,  # ChunkSize：除 RIFF+size 外的全部
        b"WAVE",
        b"fmt ",
        16,  # Subchunk1Size（PCM）
        1,  # AudioFormat = PCM
        _CHANNELS,
        samplerate,
        byte_rate,
        block_align,
        _SAMPWIDTH * 8,  # BitsPerSample
        b"data",
        data_bytes,  # Subchunk2Size
    )


def _to_int16(frame: np.ndarray) -> np.ndarray:
    """把 float32（[-1,1]）样本线性映射到 int16，越界裁剪（clip）不回绕（wrap）。

    用 32768 缩放：满幅 +1.0→+32767（裁剪上限）、-1.0→-32768（int16 下限），
    覆盖整个 int16 动态范围；超出 ±1.0 的值被裁剪到端点而非整数回绕。
    """
    f = np.asarray(frame, dtype="float32").reshape(-1)
    scaled = np.round(np.asarray(f, dtype="float64") * 32768.0)
    scaled = np.clip(scaled, -32768.0, 32767.0)
    return scaled.astype("<i2")


class DayWavWriter:
    """按天滚动的 day-WAV 的增量追加器。

    构造时若文件不存在则建头；若已存在则读出已有样本数、续写其末尾
    （守护进程重启续写当天那个 WAV，不清空）。
    """

    def __init__(self, path: str | Path, samplerate: int = config.SAMPLE_RATE) -> None:
        """打开（或新建）day-WAV，定位到末尾准备追加。

        Args:
            path: WAV 文件路径，父目录不存在时自动创建。
            samplerate: 采样率（Hz）。
        """
        self.path = Path(path)
        self.samplerate = samplerate
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if self.path.is_file() and self.path.stat().st_size >= _HEADER_SIZE:
            # 续写：从已有 data 长度字段推出已写样本数。
            raw_head = self.path.read_bytes()[:_HEADER_SIZE]
            data_bytes = struct.unpack_from("<I", raw_head, 40)[0]
            self._total_samples = data_bytes // (_CHANNELS * _SAMPWIDTH)
            self._fh = open(self.path, "r+b")
            self._fh.seek(0, 2)  # 到文件尾
        else:
            self._total_samples = 0
            self._fh = open(self.path, "w+b")
            self._fh.write(_build_header(samplerate, 0))
            self._fh.flush()

    @property
    def total_samples(self) -> int:
        """已写入的累计样本数（= day-WAV 内当前写入位置）。"""
        return self._total_samples

    def start_ms_for(self, sample: int) -> int:
        """把样本编号换算成 day-WAV 内的毫秒偏移。"""
        return int(round(sample / self.samplerate * 1000))

    def append(self, frame: np.ndarray) -> None:
        """把一块 float32 样本追加到 day-WAV 末尾，并更新头长度字段。

        Args:
            frame: 一维 float32 样本（[-1,1]，单声道）。
        """
        pcm = _to_int16(frame)
        if pcm.size == 0:
            return
        self._fh.seek(0, 2)  # 确保在文件尾
        self._fh.write(pcm.tobytes())
        self._total_samples += int(pcm.size)
        self._update_header()

    def _update_header(self) -> None:
        """回填 RIFF ChunkSize(偏移4) 与 data Subchunk2Size(偏移40) 并 flush。"""
        data_bytes = self._total_samples * _CHANNELS * _SAMPWIDTH
        self._fh.seek(4)
        self._fh.write(struct.pack("<I", 36 + data_bytes))
        self._fh.seek(40)
        self._fh.write(struct.pack("<I", data_bytes))
        self._fh.seek(0, 2)
        self._fh.flush()

    def close(self) -> None:
        """收尾：再更新一次头并关闭文件。"""
        if self._fh is not None and not self._fh.closed:
            self._update_header()
            self._fh.close()
