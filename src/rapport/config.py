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


def _parse_device(raw: str) -> int | str | None:
    """解析输入设备配置：纯数字→设备索引(int)，非空→设备名(str)，空→None(系统默认)。"""
    raw = raw.strip()
    if not raw:
        return None
    return int(raw) if raw.lstrip("-").isdigit() else raw


# 录音输入设备：空=系统默认；数字=设备索引；其他=设备名（子串匹配）。
# 用 `rapport devices` 查看可选设备。注意：远程桌面(如 ToDesk)会把虚拟声卡设成默认。
INPUT_DEVICE: int | str | None = _parse_device(_env("INPUT_DEVICE", ""))

# 语言模型后端：none（默认，未配置）/ fake（看示例）/ anthropic / ollama。
# 配 anthropic 时还需设置环境变量 ANTHROPIC_API_KEY。
LLM_PROVIDER: str = _env("LLM_PROVIDER", "none")

# 语言模型名：anthropic 默认 claude-opus-4-8（当前最强 Opus）。
LLM_MODEL: str = _env("LLM_MODEL", "claude-opus-4-8")

# Ollama（本地模型，数据不出设备，最贴产品调性）配置：
# 模型默认指向常见的 qwen2.5:7b（中文强、支持结构化输出）；想换更强的本地模型
# （如 qwen2.5:14b / qwen3）只改 RAPPORT_OLLAMA_MODEL。endpoint 默认本机 11434。
OLLAMA_MODEL: str = _env("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")
OLLAMA_HOST: str = _env("OLLAMA_HOST", "http://localhost:11434")

# 数据目录：默认指向仓库下 data/。
# 本文件位于 src/rapport/config.py，仓库根为其上溯三级父目录。
_REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR: Path = Path(_env("DATA_DIR", str(_REPO_ROOT / "data")))

# SQLite 数据库路径：默认指向 DATA_DIR/rapport.db。
DB_PATH: Path = Path(_env("DB_PATH", str(DATA_DIR / "rapport.db")))

# ---- 常驻 always-on 后台录音（M5 任务二）配置 ----------------------------
# 全部 RAPPORT_* env 可覆盖；纯逻辑（segmenter）从这里取默认，但也接受显式参数注入。

# 录音音频与 day-WAV 的存放目录：默认 DATA_DIR/audio。
AUDIO_DIR: Path = Path(_env("AUDIO_DIR", str(DATA_DIR / "audio")))

# 录制状态文件：守护进程原子写、/api/status 读。默认 DATA_DIR/recording_status.json。
RECORDING_STATUS_PATH: Path = Path(
    _env("RECORDING_STATUS_PATH", str(DATA_DIR / "recording_status.json"))
)

# 静音持续多久（毫秒）就切一句。
SILENCE_MS: int = int(_env("SILENCE_MS", "700"))

# 单句最大时长（秒），到顶强切，防一句无限长。
MAX_UTTERANCE_S: float = float(_env("MAX_UTTERANCE_S", "30"))

# 单句最小时长（秒），不足则丢弃（纯静音/噪声段不入库）。
MIN_UTTERANCE_S: float = float(_env("MIN_UTTERANCE_S", "1"))

# 静音判定的 RMS 能量阈值（float32 幅度，归一化到 [-1,1]）。
# 0.01 约等于 -40 dBFS：典型室内底噪在其下、正常说话在其上，是常用的语音活动门限。
SILENCE_RMS_THRESHOLD: float = float(_env("SILENCE_RMS_THRESHOLD", "0.01"))


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
