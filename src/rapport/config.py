"""简单配置：模块常量 + 环境变量覆盖（前缀 RAPPORT_）。"""

from __future__ import annotations

import os
from pathlib import Path

from .transcribe.base import Transcriber

# 环境变量前缀
_ENV_PREFIX = "RAPPORT_"


def _env(name: str, default: str) -> str:
    """读取带前缀的环境变量，缺省时返回 default。"""
    return os.environ.get(_ENV_PREFIX + name, default)


# 选用的转写实现：local 表示本地 faster-whisper。
TRANSCRIBER: str = _env("TRANSCRIBER", "local")

# faster-whisper 模型名（如 tiny / base / small / medium / large-v3）。
WHISPER_MODEL: str = _env("WHISPER_MODEL", "base")

# 运行设备：cpu（默认，处处能跑，无需 CUDA）/ cuda（需 CUDA 运行库）/ auto（试探 cuda，失败回退 cpu）。
WHISPER_DEVICE: str = _env("WHISPER_DEVICE", "cpu")

# 计算精度：default / int8 / float16 等。
WHISPER_COMPUTE_TYPE: str = _env("WHISPER_COMPUTE_TYPE", "default")

# 录音采样率（Hz）。
SAMPLE_RATE: int = int(_env("SAMPLE_RATE", "16000"))

# 录音声道数。
CHANNELS: int = int(_env("CHANNELS", "1"))

# 数据目录：默认指向仓库下 data/。
# 本文件位于 src/rapport/config.py，仓库根为其上溯三级父目录。
_REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR: Path = Path(_env("DATA_DIR", str(_REPO_ROOT / "data")))


def get_transcriber() -> Transcriber:
    """按 TRANSCRIBER 配置返回对应的转写器实现。

    local 分支内延迟导入 LocalWhisperTranscriber，
    以免未安装 faster-whisper 时整包导入失败。

    Returns:
        Transcriber 实例。

    Raises:
        ValueError: TRANSCRIBER 取值不被支持时。
    """
    if TRANSCRIBER == "local":
        from .transcribe.local_whisper import LocalWhisperTranscriber

        return LocalWhisperTranscriber(
            model=WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE,
        )
    raise ValueError(f"不支持的 TRANSCRIBER 取值：{TRANSCRIBER!r}")
