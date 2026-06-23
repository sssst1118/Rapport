"""常驻引擎：串起采集 → 切句 → 转写 → 分离 → 续写当天 conversation → 落 day-WAV。

把硬件/线程隔在「音频源」之外，引擎本身的处理管线（feed 一帧 → 切句 → 入库）
是纯逻辑、可注入假源/假转写器/假分离器/内存库/时钟来确定性单测。
真实运行时音频源用 Recorder 的 InputStream 回调喂帧（见 __main__.watch）。

时间坐标：day-WAV 是「当天连续录音」。recording 且未 paused 时，每帧立即追加到
day-WAV，推进 day-WAV 样本计数；segmenter 跑在同一套样本坐标上。每条 utterance 的
start_ms/end_ms = 它在 day-WAV 里的样本偏移 / 采样率 * 1000。**暂停时整帧丢弃、
不写 day-WAV、不推进坐标**，因此恢复后续写 day-WAV 末尾，时间戳天然连续、不含暂停时段。
"""

from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import numpy as np

from .. import config
from .daywav import DayWavWriter
from .segmenter import Segmenter
from .status import clear_status, write_status

if TYPE_CHECKING:
    from ..diarize.base import Diarizer
    from ..storage.db import Database
    from ..transcribe.base import Transcriber


class AudioSource(Protocol):
    """音频源契约：start(callback) 后持续把帧交给 callback，stop() 停止。

    真实实现 = 麦克风 InputStream 回调；测试实现 = 手动喂帧的假源。
    """

    def start(self, callback) -> None:  # noqa: ANN001
        """开始采集，每块音频帧调用 callback(frame: np.ndarray[float32])。"""
        ...

    def stop(self) -> None:
        """停止采集。"""
        ...


class _SystemClock:
    """默认时钟：返回本地自然日字符串（YYYY-MM-DD）。"""

    def today_str(self) -> str:
        from datetime import date

        return date.today().isoformat()


class Engine:
    """常驻录音引擎。

    生命周期：start() → 持续 feed 帧 → 可 pause()/resume() → stop()。
    """

    def __init__(
        self,
        db: Database,
        transcriber: Transcriber,
        diarizer: Diarizer,
        audio_source: AudioSource,
        *,
        clock=None,  # noqa: ANN001
        audio_dir: str | Path | None = None,
        status_path: str | Path | None = None,
        samplerate: int = config.SAMPLE_RATE,
        silence_ms: int = config.SILENCE_MS,
        max_utterance_s: float = config.MAX_UTTERANCE_S,
        min_utterance_s: float = config.MIN_UTTERANCE_S,
        silence_rms_threshold: float = config.SILENCE_RMS_THRESHOLD,
        repo_root: str | Path | None = None,
    ) -> None:
        """构造引擎。

        Args:
            db: 已打开的数据库门面（其连接须与 feed 调用同线程）。
            transcriber: 转写器（真实或假）。
            diarizer: 分离器（真实或假）。
            audio_source: 音频源（真实麦克风或假源）。
            clock: 注入时钟，需有 today_str()->str；None 用系统时钟。
            audio_dir: day-WAV 存放目录；None 取 config.AUDIO_DIR。
            status_path: 状态文件路径；None 取 config.RECORDING_STATUS_PATH。
            samplerate: 采样率（Hz）。
            silence_ms/max_utterance_s/min_utterance_s/silence_rms_threshold: 切句参数。
            repo_root: 计算写库 audio_path 的相对基准；None 取仓库根（与 web 一致）。
        """
        self._db = db
        self._transcriber = transcriber
        self._diarizer = diarizer
        self._source = audio_source
        self._clock = clock or _SystemClock()
        self._audio_dir = Path(audio_dir) if audio_dir is not None else config.AUDIO_DIR
        self._status_path = (
            Path(status_path)
            if status_path is not None
            else config.RECORDING_STATUS_PATH
        )
        self._samplerate = samplerate
        self._seg_kwargs = dict(
            silence_ms=silence_ms,
            max_utterance_s=max_utterance_s,
            min_utterance_s=min_utterance_s,
            silence_rms_threshold=silence_rms_threshold,
        )
        # 写库 audio_path 用相对仓库根的路径，跟 web /api/.../audio 的解析一致。
        self._repo_root = (
            Path(repo_root)
            if repo_root is not None
            else Path(config.__file__).resolve().parents[2]
        )

        self._recording = False
        self._paused = False

        # 当天上下文（按天滚动时重建）。
        self._day: str | None = None
        self._cid: int | None = None
        self._writer: DayWavWriter | None = None
        self._segmenter: Segmenter | None = None
        # 样本缓冲：保留「当前未闭合 utterance 起点」之后的样本，供切句后切片转写。
        self._buf: list[np.ndarray] = []
        self._buf_start: int = 0  # buffer 首样本在 day-WAV 中的绝对样本编号

    # ---- 状态 ----------------------------------------------------------

    @property
    def recording(self) -> bool:
        """是否正在录音（已 start 未 stop）。"""
        return self._recording

    @property
    def paused(self) -> bool:
        """是否处于暂停（停止采集入库，但仍在录音会话内）。"""
        return self._paused

    def _publish_status(self) -> None:
        """把当前状态原子写到状态文件。"""
        write_status(
            self._status_path, recording=self._recording, paused=self._paused
        )

    # ---- 生命周期 ------------------------------------------------------

    def start(self) -> None:
        """开始录音：写状态、打开音频源（帧回调进 _on_frame）。"""
        if self._recording:
            return
        self._recording = True
        self._paused = False
        self._publish_status()
        self._source.start(self._on_frame)

    def pause(self) -> None:
        """暂停：完全停止采集入库（隐私优先）。当前未闭合句先 finalize。"""
        if not self._recording or self._paused:
            return
        self._flush_pending()
        self._paused = True
        self._publish_status()

    def resume(self) -> None:
        """恢复：接着当天 day-WAV 末尾续写，时间戳连续不含暂停时段。"""
        if not self._recording or not self._paused:
            return
        self._paused = False
        self._publish_status()

    def stop(self) -> None:
        """停止：finalize 当前句、关 day-WAV、停音频源、清状态文件。幂等。"""
        if not self._recording:
            return
        try:
            self._source.stop()
        except Exception:  # noqa: BLE001 - 假源/真源停时都尽力收尾
            pass
        self._flush_pending()
        if self._writer is not None:
            self._writer.close()
            self._writer = None
        self._segmenter = None
        self._buf = []
        self._buf_start = 0
        self._day = None
        self._cid = None
        self._recording = False
        self._paused = False
        clear_status(self._status_path)

    # ---- 帧处理（核心管线） --------------------------------------------

    def _on_frame(self, frame: np.ndarray) -> None:
        """音频源回调：处理一块帧。暂停或未录音时整帧丢弃。"""
        if not self._recording or self._paused:
            return
        frame = np.asarray(frame, dtype="float32").reshape(-1)
        if frame.size == 0:
            return

        self._ensure_day_context()
        assert self._writer is not None and self._segmenter is not None

        # 1) 立即把帧写进当天 day-WAV，推进 day-WAV 坐标。
        self._writer.append(frame)
        # 2) 缓冲样本，供切句后切片转写。
        self._buf.append(frame)
        # 3) 喂 segmenter，处理它吐出的每条 utterance。
        for utt in self._segmenter.push(frame):
            self._handle_utterance(utt.start_sample, utt.end_sample)

    def _ensure_day_context(self) -> None:
        """确保「今天」的 conversation / day-WAV / segmenter 就绪；跨天则滚动。"""
        today = self._clock.today_str()
        if self._day == today and self._writer is not None:
            return
        # 跨天：先 finalize 旧的一天。
        if self._day is not None:
            self._flush_pending()
            if self._writer is not None:
                self._writer.close()
                self._writer = None

        wav_path = self._audio_dir / f"{today}.wav"
        rel_path = self._rel_audio_path(wav_path)
        self._cid = self._db.get_or_create_daily_conversation(
            today, audio_path=rel_path
        )
        self._writer = DayWavWriter(wav_path, samplerate=self._samplerate)
        self._segmenter = Segmenter(samplerate=self._samplerate, **self._seg_kwargs)
        self._buf = []
        # 续写已有 day-WAV 时，新句的坐标从已写样本数接着算。
        self._buf_start = self._writer.total_samples
        # segmenter 坐标也要对齐到 day-WAV 已写位置，否则续写的偏移会从 0 重来。
        self._segmenter.seek_to(self._writer.total_samples)
        self._day = today

    def _rel_audio_path(self, wav_path: Path) -> str:
        """把 day-WAV 绝对路径转成相对仓库根的 posix 路径（web 解析的基准）。"""
        wav_path = wav_path.resolve()
        try:
            return wav_path.relative_to(self._repo_root).as_posix()
        except ValueError:
            # 不在仓库根下（如测试用 tmp_path）：退回绝对 posix 路径，web 也能拼。
            return wav_path.as_posix()

    def _flush_pending(self) -> None:
        """finalize segmenter 里最后一段未闭合的句子（若够长）。"""
        if self._segmenter is None:
            return
        utt = self._segmenter.flush()
        if utt is not None:
            self._handle_utterance(utt.start_sample, utt.end_sample)

    def _handle_utterance(self, start_sample: int, end_sample: int) -> None:
        """切一句：从缓冲取样本 → 临时 WAV → 转写 → 分离 → 写库（带 day-WAV 偏移）。"""
        assert self._writer is not None and self._cid is not None
        samples = self._slice_buffer(start_sample, end_sample)
        if samples.size == 0:
            return

        start_ms = self._writer.start_ms_for(start_sample)
        end_ms = self._writer.start_ms_for(end_sample)

        # 把这句样本临时落一个小 WAV 交给转写器（最终 utterance 的音频出处仍是 day-WAV）。
        with tempfile.TemporaryDirectory() as td:
            clip = Path(td) / "clip.wav"
            self._write_clip(clip, samples)
            segments = self._transcriber.transcribe(str(clip))

        # 用 day-WAV 绝对偏移覆盖转写器返回的片段内相对偏移，保证 🔊 跳播对齐。
        from ..transcribe.base import Segment

        rebased = [
            Segment(
                text=s.text,
                start_ms=start_ms,
                end_ms=end_ms,
                speaker_label=s.speaker_label,
            )
            for s in segments
        ]
        rebased = self._diarizer.diarize(str(self._writer.path), rebased)
        if rebased:
            self._db.add_segments(self._cid, rebased)

    def _slice_buffer(self, start_sample: int, end_sample: int) -> np.ndarray:
        """从样本缓冲取 [start_sample, end_sample) 区间，并把缓冲裁到 end_sample。"""
        if not self._buf:
            return np.zeros(0, dtype="float32")
        data = np.concatenate(self._buf)
        avail_start = self._buf_start
        i = max(0, start_sample - avail_start)
        j = max(i, end_sample - avail_start)
        out = data[i:j].copy()
        # 裁掉已消费到 end_sample 的部分，保留之后的样本（可能属下一句开头）。
        keep_from = max(0, end_sample - avail_start)
        remainder = data[keep_from:]
        if remainder.size:
            self._buf = [remainder]
            self._buf_start = end_sample
        else:
            self._buf = []
            self._buf_start = end_sample
        return out

    def _write_clip(self, path: Path, samples: np.ndarray) -> None:
        """把一段 float32 样本写成 16-bit 单声道 WAV（供转写器读）。"""
        pcm = np.clip(np.round(samples.astype("float64") * 32768.0), -32768, 32767)
        pcm = pcm.astype("<i2")
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self._samplerate)
            w.writeframes(pcm.tobytes())
