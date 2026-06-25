"""PyannoteDiarizer：真·多说话人分离的薄封装（pyannote.audio，可选依赖、延迟导入）。

设计要点：
- **延迟导入**：``pyannote.audio`` / ``torch`` 是 ~GB 的可选依赖（extra ``diarize``）。
  本模块顶部**不**导入它们，整包 ``import rapport.diarize`` 在未装时不炸；只有真正
  构造 ``PyannoteDiarizer()`` 时才尝试 import，未装则抛带安装指引的清晰 ImportError。
- **纯逻辑外移**：时间轴对齐（pyannote 秒级时段 ↔ whisper 毫秒句子）走 align.py 的纯
  函数 ``assign_speaker_labels``，本类只负责「跑模型 → 规整 turns → 调纯函数」。

配置（env / config.json，照 transcriber 风格）：
- ``RAPPORT_DIARIZER=pyannote`` 选用本实现（见 ``__init__.py`` 工厂）。
- ``RAPPORT_PYANNOTE_MODEL``：模型名或本地 checkpoint 路径，默认
  ``pyannote/speaker-diarization-3.1``；指向本地路径可离线。
- HF token：读 ``HUGGINGFACE_TOKEN`` / ``HF_TOKEN`` 环境变量（pyannote 预训练模型需
  接受 license + token）。token 缺失时给出清晰报错指引。

已知限制：A/B/C 仅在**单次 diarize 调用内**一致；跨调用/跨天对话不保证同一人=同一
标签（pyannote 每次独立给 SPEAKER_xx）。跨对话认人需声纹 embedding，属后置阶段。
"""

from __future__ import annotations

import os

from ..config import _env
from ..transcribe.base import Segment
from .align import assign_speaker_labels
from .base import Diarizer

# 模型名 / 本地 checkpoint 路径，默认官方 3.1。
PYANNOTE_MODEL: str = _env("PYANNOTE_MODEL", "pyannote/speaker-diarization-3.1")

_安装指引 = (
    'pyannote.audio 未安装，请 pip install -e ".[diarize]" '
    "并参见 README 接受模型 license + 配置 HF token"
    "（HUGGINGFACE_TOKEN 或 HF_TOKEN 环境变量）"
)


def _resolve_hf_token() -> str | None:
    """读 HF token：HUGGINGFACE_TOKEN > HF_TOKEN > None。"""
    return os.environ.get("HUGGINGFACE_TOKEN") or os.environ.get("HF_TOKEN")


class PyannoteDiarizer(Diarizer):
    """用 pyannote.audio 做真·多说话人分离，按时间重叠把句子赋 A/B/C…。

    构造时即延迟 import 并加载 pipeline（fail-fast：未装依赖 / 缺 token 立即报错，
    而非等到第一次 diarize）。
    """

    def __init__(self, model: str | None = None) -> None:
        """加载 pyannote pipeline。

        Args:
            model: 模型名或本地 checkpoint 路径；缺省用 ``PYANNOTE_MODEL`` 配置。

        Raises:
            ImportError: 未安装 pyannote.audio 时，附 extra 安装与 token 指引。
            ValueError: 缺 HF token 且模型不是本地路径时。
        """
        try:
            from pyannote.audio import Pipeline
        except ImportError as exc:  # pragma: no cover - 装了就不会进这里
            raise ImportError(_安装指引) from exc

        self._model = model or PYANNOTE_MODEL
        token = _resolve_hf_token()
        # 本地 checkpoint（存在的路径）可离线、无需 token；否则下载预训练需 token。
        if token is None and not os.path.exists(self._model):
            raise ValueError(
                f"加载预训练模型 {self._model!r} 需 HF token：请设 HUGGINGFACE_TOKEN "
                "或 HF_TOKEN 环境变量，并先在 HuggingFace 上接受该模型 license"
                "（或把 RAPPORT_PYANNOTE_MODEL 指向已下载的本地 checkpoint 以离线运行）"
            )
        # context7 核对（pyannote/pyannote-audio 当前文档）：参数名是 token=，
        # 非旧版 use_auth_token=。token=None 时本地路径可正常加载。
        self._pipeline = Pipeline.from_pretrained(self._model, token=token)

    def diarize(self, audio_path: str, segments: list[Segment]) -> list[Segment]:
        """跑 pyannote 得到说话人时段，对齐到转写句子并赋 A/B/C…。

        Args:
            audio_path: 原始音频文件路径。
            segments: 转写得到的句子列表。

        Returns:
            带 speaker_label（A/B/C…，无重叠句为 None）的新 Segment 列表。
        """
        if not segments:
            return []
        diarization = self._pipeline(audio_path)
        turns = _diarization_to_turns(diarization)
        return assign_speaker_labels(segments, turns)


def _diarization_to_turns(diarization: object) -> list[tuple[str, int, int]]:
    """把 pyannote diarization 结果规整成 ``[(speaker_key, start_ms, end_ms), ...]``。

    context7 核对（pyannote/pyannote-audio 当前文档）：3.1 直接返回 Annotation，
    用 ``for segment, _track, speaker in diarization.itertracks(yield_label=True)``
    迭代，``segment.start`` / ``segment.end`` 为**秒**。新版 community-1 返回复合对象、
    说话人时段在 ``.speaker_diarization`` 属性下——故先做兼容取值再迭代。
    """
    annotation = getattr(diarization, "speaker_diarization", diarization)
    turns: list[tuple[str, int, int]] = []
    for segment, _track, speaker in annotation.itertracks(yield_label=True):
        turns.append(
            (str(speaker), int(segment.start * 1000), int(segment.end * 1000))
        )
    return turns
