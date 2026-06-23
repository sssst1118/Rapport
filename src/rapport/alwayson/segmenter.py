"""分段引擎：纯逻辑，对一串音频帧做静音切分，决定 utterance 边界。

刻意**不 import sounddevice / numpy 之外的任何硬件依赖**（numpy 仅用于算 RMS，
与转写/采集无关），让本模块零硬件依赖、可像 test_ingest.py 一样纯单测。

切分规则（默认值取自 config，可显式覆盖）：
- 帧 RMS 低于 `silence_rms_threshold` 视为静音；
- 静音持续超过 `silence_ms` → 切出当前这一句；
- 单句到达 `max_utterance_s` 上限 → 强切（防一句无限长）；
- 切出的句子时长不足 `min_utterance_s` → 丢弃（纯静音/噪声不入库）。

样本编号语义：Segmenter 维护「已 push 的累计样本数」作为坐标系，
每个 Utterance 的 (start_sample, end_sample) 都相对这个累计坐标。
引擎只在「未暂停」时把帧 push 进来，因此该坐标天然等价于 day-WAV 里的写入位置，
暂停时段不被计入——start_ms/end_ms 据此换算即可自然跳过暂停。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .. import config


@dataclass
class Utterance:
    """切出的一句话语的样本区间（半开区间 [start_sample, end_sample)）。

    Attributes:
        start_sample: 起始样本编号（相对累计坐标）。
        end_sample: 结束样本编号（不含）。
    """

    start_sample: int
    end_sample: int


def _rms(frame: np.ndarray) -> float:
    """计算一帧（float32，[-1,1]）的均方根能量；空帧返回 0。"""
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(frame, dtype="float64"))))


class Segmenter:
    """有状态的流式静音切分器：逐帧 push，到边界时吐出 Utterance。

    用法：对每个采集到的音频块调用 push() 收集返回的（可能为空的）句子列表；
    采集结束时调用 flush() 取出最后一段未闭合的句子（若有）。
    """

    def __init__(
        self,
        samplerate: int = config.SAMPLE_RATE,
        *,
        silence_ms: int = config.SILENCE_MS,
        max_utterance_s: float = config.MAX_UTTERANCE_S,
        min_utterance_s: float = config.MIN_UTTERANCE_S,
        silence_rms_threshold: float = config.SILENCE_RMS_THRESHOLD,
    ) -> None:
        """构造切分器。

        Args:
            samplerate: 采样率（Hz）。
            silence_ms: 静音持续多久（毫秒）切一句。
            max_utterance_s: 单句最大时长（秒），到顶强切。
            min_utterance_s: 单句最小时长（秒），不足则丢弃。
            silence_rms_threshold: 静音判定的 RMS 阈值。
        """
        self.samplerate = samplerate
        self._silence_samples = int(round(silence_ms / 1000.0 * samplerate))
        self._max_samples = int(round(max_utterance_s * samplerate))
        self._min_samples = int(round(min_utterance_s * samplerate))
        self._threshold = silence_rms_threshold

        self._total = 0  # 已 push 的累计样本数（坐标系原点）
        self._cur_start: int | None = None  # 当前句的起点；None=不在句中
        self._cur_end = 0  # 当前句最后一个「有声」样本之后的位置
        self._trailing_silence = 0  # 当前句尾部已累计的静音样本数

    def seek_to(self, sample: int) -> None:
        """把累计样本坐标对齐到指定位置（续写已有 day-WAV 时让偏移从其末尾接着算）。

        只在「不在句中」时调用（刚构造或刚 flush）。

        Args:
            sample: 新的累计样本原点（通常是 day-WAV 已写样本数）。
        """
        self._total = sample

    def push(self, frame: np.ndarray) -> list[Utterance]:
        """喂入一块音频帧，返回此块触发完成的句子（可能为空，可能多条）。

        Args:
            frame: 一维 float32 样本数组（[-1,1]，单声道）。

        Returns:
            本次触发闭合的 Utterance 列表（按时间序）。
        """
        out: list[Utterance] = []
        n = int(frame.size)
        if n == 0:
            return out
        block_start = self._total
        self._total += n

        voiced = _rms(frame) >= self._threshold

        if voiced:
            if self._cur_start is None:
                self._cur_start = block_start
            self._cur_end = block_start + n
            self._trailing_silence = 0
        else:
            if self._cur_start is not None:
                self._trailing_silence += n
                if self._trailing_silence >= self._silence_samples:
                    # 静音够久：闭合当前句（end 用最后有声位置，不含尾部静音）
                    u = self._emit()
                    if u is not None:
                        out.append(u)

        # 最大时长强切：当前句已积累到上限就立刻切（即便仍在持续有声）。
        while self._cur_start is not None and (
            self._total - self._cur_start
        ) >= self._max_samples:
            forced_end = self._cur_start + self._max_samples
            u = self._emit_at(forced_end)
            if u is not None:
                out.append(u)
        return out

    def flush(self) -> Utterance | None:
        """采集结束时取出最后一段未闭合的句子（若够长），否则返回 None。"""
        return self._emit()

    def _emit(self) -> Utterance | None:
        """以「最后有声位置」为终点闭合当前句并复位状态。"""
        if self._cur_start is None:
            return None
        return self._emit_at(self._cur_end)

    def _emit_at(self, end_sample: int) -> Utterance | None:
        """以指定终点闭合当前句；过短则丢弃。强切后续写从 end_sample 接着算。"""
        assert self._cur_start is not None
        start = self._cur_start
        length = end_sample - start
        # 复位：强切时当前块可能仍在有声，让剩余部分作为新句的开头继续累计。
        if end_sample < self._cur_end:
            # 强切：still 有声，新句从 end_sample 接着开始
            self._cur_start = end_sample
            self._trailing_silence = 0
        else:
            self._cur_start = None
            self._cur_end = 0
            self._trailing_silence = 0
        if length < self._min_samples:
            return None
        return Utterance(start_sample=start, end_sample=end_sample)
