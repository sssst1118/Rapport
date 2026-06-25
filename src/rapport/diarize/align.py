"""纯对齐算法：把 pyannote 说话人时段对齐到 whisper 转写句子。

本模块**零重依赖**（不 import torch / pyannote / numpy），是说话人分离的核心逻辑，
单独抽出来好做纯单测。pyannote 的薄封装（pyannote_diarizer.py）先把 diarization
规整成 ``turns``（毫秒），再调本模块的 ``assign_speaker_labels`` 给每句赋 A/B/C…。

范围：**单次 diarize 调用内**的多说话人区分。raw_speaker_key（如 "SPEAKER_00"）
按在本次结果里**首次出现的顺序**重映射为 A/B/C…——与现有 "A" 风格一致、对用户友好、
且幂等（同输入同输出）。跨调用/跨天对话不保证同标签（pyannote 每次独立给 SPEAKER_xx）。
"""

from __future__ import annotations

from dataclasses import replace

from ..transcribe.base import Segment


def assign_speaker_labels(
    segments: list[Segment], turns: list[tuple[str, int, int]]
) -> list[Segment]:
    """按时间重叠把说话人时段映射到转写句子，返回带 A/B/C… 标签的新列表。

    算法：
    1. 对每个 Segment，遍历 turns 累计与各 raw_speaker_key 的时间重叠总量
       ``overlap = max(0, min(seg.end_ms, turn_end) - max(seg.start_ms, turn_start))``，
       取重叠**总量最大**者为该句说话人；无任何重叠则保持 None（边界/静音）。
    2. 把选中的 raw_speaker_key 按**首次出现顺序**重映射成 A/B/C…（幂等）。
    3. 用 ``dataclasses.replace`` 返回新 Segment，不改原对象。

    Args:
        segments: whisper 转写句子（毫秒时间戳）。
        turns: pyannote 说话人时段，``[(raw_speaker_key, start_ms, end_ms), ...]``。

    Returns:
        speaker_label 为 A/B/C…（无重叠句为 None）的新 Segment 列表。
    """
    # 第一遍：为每句选出重叠总量最大的 raw_speaker_key（无重叠 → None）。
    chosen_keys: list[str | None] = []
    for seg in segments:
        overlap_by_key: dict[str, int] = {}
        for raw_key, t_start, t_end in turns:
            overlap = min(seg.end_ms, t_end) - max(seg.start_ms, t_start)
            if overlap > 0:
                overlap_by_key[raw_key] = overlap_by_key.get(raw_key, 0) + overlap
        if overlap_by_key:
            # 取重叠总量最大者；并列时取首个遇到的 key（dict 保序，稳定可复现）。
            best = max(overlap_by_key, key=lambda k: overlap_by_key[k])
            chosen_keys.append(best)
        else:
            chosen_keys.append(None)

    # 第二遍：raw_speaker_key → A/B/C…，按首次出现顺序分配（幂等）。
    label_of: dict[str, str] = {}
    result: list[Segment] = []
    for seg, key in zip(segments, chosen_keys):
        if key is None:
            result.append(replace(seg, speaker_label=None))
            continue
        if key not in label_of:
            label_of[key] = chr(ord("A") + len(label_of))
        result.append(replace(seg, speaker_label=label_of[key]))
    return result
