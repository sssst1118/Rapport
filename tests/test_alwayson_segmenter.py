"""分段引擎（segmenter）纯逻辑测试：合成帧 → 断言切句边界。

全部不依赖真麦克风、真 whisper：只构造 numpy 合成帧喂给 Segmenter，
断言切出的 utterance 段数、样本边界、最大时长强切、过短丢弃。
"""

from __future__ import annotations

import numpy as np

from rapport.alwayson.segmenter import Segmenter

_SR = 16000  # 测试统一用 16kHz


def _voiced(n_samples: int, amp: float = 0.2) -> np.ndarray:
    """合成一段「有声」帧（RMS 明显高于静音阈值）。"""
    return np.full(n_samples, amp, dtype="float32")


def _silence(n_samples: int) -> np.ndarray:
    """合成一段「静音」帧（全零，RMS=0）。"""
    return np.zeros(n_samples, dtype="float32")


def _collect(seg: Segmenter, frames: list[np.ndarray]) -> list:
    """把若干帧依次 push 进 segmenter，最后 flush，收集所有 utterance。"""
    out = []
    for f in frames:
        out.extend(seg.push(f))
    last = seg.flush()
    if last is not None:
        out.append(last)
    return out


def test_单段有声被静音切成一句() -> None:
    # 1s 有声 → 1s 静音（>700ms 静音阈值）→ 应切出恰好一句
    seg = Segmenter(samplerate=_SR)
    utts = _collect(seg, [_voiced(_SR), _silence(_SR)])
    assert len(utts) == 1
    # 该句样本区间应覆盖那 1s 有声（约 [0, 16000)），不含尾部静音
    assert utts[0].start_sample == 0
    assert utts[0].end_sample <= _SR + int(0.7 * _SR)  # 至多含触发静音那点
    assert utts[0].end_sample >= _SR  # 至少覆盖整段有声


def test_两句话被中间静音分开() -> None:
    # 有声 → 长静音 → 有声 → 长静音 → 应切出两句
    seg = Segmenter(samplerate=_SR)
    utts = _collect(
        seg,
        [_voiced(_SR), _silence(_SR), _voiced(_SR), _silence(_SR)],
    )
    assert len(utts) == 2
    # 第二句起点应在第一段静音之后（样本编号连续递增）
    assert utts[1].start_sample > utts[0].end_sample


def test_短于静音阈值的停顿不切句() -> None:
    # 中间只静 300ms（<700ms 默认阈值）→ 仍是一整句
    seg = Segmenter(samplerate=_SR)
    short_gap = _silence(int(0.3 * _SR))
    utts = _collect(seg, [_voiced(_SR), short_gap, _voiced(_SR), _silence(_SR)])
    assert len(utts) == 1


def test_超过最大时长强切() -> None:
    # 持续有声 70s、无静音 → MAX_UTTERANCE_S=30 应至少强切成 2 句
    seg = Segmenter(samplerate=_SR, max_utterance_s=30.0)
    # 一次喂一大块连续有声（70s）
    utts = _collect(seg, [_voiced(70 * _SR)])
    assert len(utts) >= 2
    # 每句时长都不超过 30s 对应的样本数（含一帧容差）
    for u in utts:
        assert (u.end_sample - u.start_sample) <= 30 * _SR + 1


def test_过短的段被丢弃() -> None:
    # 只有 0.3s 有声（<MIN_UTTERANCE_S=1s）→ 应被丢弃，不产生 utterance
    seg = Segmenter(samplerate=_SR, min_utterance_s=1.0)
    utts = _collect(seg, [_voiced(int(0.3 * _SR)), _silence(_SR)])
    assert utts == []


def test_全静音不产生任何句() -> None:
    seg = Segmenter(samplerate=_SR)
    utts = _collect(seg, [_silence(3 * _SR)])
    assert utts == []


def test_样本计数跨多次push连续() -> None:
    # 分多次小块推送同样的「有声→静音」，边界应基于累计样本编号
    seg = Segmenter(samplerate=_SR)
    # 先推 0.5s 静音垫底，再 1s 有声，再 1s 静音
    pad = int(0.5 * _SR)
    utts = _collect(seg, [_silence(pad), _voiced(_SR), _silence(_SR)])
    assert len(utts) == 1
    # 有声从第 pad 个样本附近开始
    assert utts[0].start_sample >= pad - 1
    assert utts[0].start_sample <= pad + 1
