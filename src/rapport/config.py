"""配置：环境变量 > config.json > 内置默认（三档优先级）。

历史上本模块只有「模块常量 + RAPPORT_ 环境变量覆盖」。M5.5 起增加一层
**config.json 配置文件**（落在 ``data_root()/config.json``，冻结态即
``%LOCALAPPDATA%\\Rapport\\config.json``），让打包的 .exe 不靠环境变量也能配
语言模型等项。

优先级对每个可配置项一致：**环境变量 > config.json > 内置默认**。这样
CLI / 老用法（设环境变量）优先级最高、行为不变；打包用户改 config.json 即生效；
都没有则用默认。

config.json 每次按需新鲜读取（文件极小、调用不频繁），不缓存——好处是设置页
（Task 3）写完即时生效，无需失效逻辑；测试间也不会因缓存串状态。文件不存在或
内容损坏（坏 JSON）一律当作空配置，绝不抛。

LLM 相关项（provider/model/ollama/anthropic key）做成**调用时解析**（见模块级
``__getattr__`` 与 ``anthropic_api_key()``），改 config.json 无需重启即按下次解读
生效。whisper / 输入设备等在引擎/转写器**启动时**构造，故改动**下次启动**生效。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import _frozen
from .transcribe.base import Transcriber

# 环境变量前缀
_ENV_PREFIX = "RAPPORT_"


def _env(name: str, default: str) -> str:
    """读取带前缀的环境变量，缺省时返回 default。"""
    return os.environ.get(_ENV_PREFIX + name, default)


def _load_config_file() -> dict[str, Any]:
    """读 ``data_root()/config.json`` 返回 dict；缺失/坏 JSON/读不了 → ``{}``。

    每次调用都新鲜读一次（不缓存）：文件极小、调用不频繁，这样设置页写完即时
    生效，也避免测试间状态串。任何异常（文件不存在、JSON 解析失败、IO 错误、
    顶层不是对象）都吞掉、返回空字典——配置层绝不让应用崩。
    """
    try:
        path = _frozen.data_root() / "config.json"
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _setting(env_name: str, file_key: str, default: Any) -> Any:
    """按优先级解析一项：env ``RAPPORT_<env_name>`` > config.json[file_key] > default。

    config.json 里该键为 ``None``（显式 null）视同未设、继续回退。
    """
    env_val = os.environ.get(_ENV_PREFIX + env_name)
    if env_val is not None:
        return env_val
    file_val = _load_config_file().get(file_key)
    if file_val is not None:
        return file_val
    return default


def anthropic_api_key() -> str | None:
    """Anthropic key：裸 env ``ANTHROPIC_API_KEY`` > config.json ``anthropic_api_key`` > None。

    注意此项的环境变量**无 RAPPORT_ 前缀**（沿用 anthropic SDK 的约定），故单独
    特判、不走 ``_setting``。返回 None 表示未配置（交由 SDK 自行报缺 key）。
    """
    env_val = os.environ.get("ANTHROPIC_API_KEY")
    if env_val is not None:
        return env_val
    file_val = _load_config_file().get("anthropic_api_key")
    return file_val if isinstance(file_val, str) and file_val else None


def save_config(updates: dict[str, Any]) -> None:
    """把 ``updates`` 合并进 ``data_root()/config.json`` 并**原子写**（给 Task 3 设置页复用）。

    读现有内容（不存在/坏 JSON 当 ``{}``），用 ``updates`` 浅合并（只覆盖传入键，
    不清空其余键），写临时文件后 ``os.replace`` 原子落定，避免写一半被读到。
    目标目录不存在时先 ``mkdir(parents=True)``。
    """
    root = _frozen.data_root()
    root.mkdir(parents=True, exist_ok=True)
    merged = _load_config_file()
    merged.update(updates)
    path = root / "config.json"
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(tmp, path)


# ---- 调用时解析的 LLM 项（模块级 __getattr__） ---------------------------
#
# 这几项不写成 import 期模块常量，而是经下面的 __getattr__ 在**每次属性访问时**
# 解析（env > config.json > 默认）。analysis.get_provider() / 各 provider 都在调用
# 时读 config.LLM_PROVIDER / LLM_MODEL / OLLAMA_*，于是改 config.json 无需重启即按
# 下次解读生效（热生效）。
#
# 同时这保持「可被 monkeypatch 覆盖」：测试里 monkeypatch.setattr(config,
# "LLM_PROVIDER", "fake") 会在模块 __dict__ 写真实属性，PEP 562 的 __getattr__
# 只在常规查找失败时触发，故被覆盖期间走真实属性、测后撤销又回到动态解析。
_DYNAMIC: dict[str, tuple[str, str, str]] = {
    # 属性名: (env 子名, config.json 键, 默认值)
    "LLM_PROVIDER": ("LLM_PROVIDER", "llm_provider", "none"),
    "LLM_MODEL": ("LLM_MODEL", "llm_model", "claude-opus-4-8"),
    "OLLAMA_MODEL": ("OLLAMA_MODEL", "ollama_model", "qwen2.5:7b-instruct-q4_K_M"),
    "OLLAMA_HOST": ("OLLAMA_HOST", "ollama_host", "http://localhost:11434"),
}


def __getattr__(name: str) -> Any:
    """PEP 562 模块级动态属性：LLM 项调用时解析（env > config.json > 默认）。"""
    spec = _DYNAMIC.get(name)
    if spec is not None:
        return _setting(*spec)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# 选用的转写实现：local 表示本地 faster-whisper。
TRANSCRIBER: str = _env("TRANSCRIBER", "local")

# faster-whisper 模型名（如 tiny / base / small / medium / large-v3）。
# 接入 config.json（whisper_model）；引擎启动时构造，改动下次启动生效。
WHISPER_MODEL: str = _setting("WHISPER_MODEL", "whisper_model", "base")

# 运行设备：cpu（默认，处处能跑，无需 CUDA）/ cuda（需 CUDA 运行库）/ auto（试探 cuda，失败回退 cpu）。
# 接入 config.json（whisper_device）；下次启动生效。
WHISPER_DEVICE: str = _setting("WHISPER_DEVICE", "whisper_device", "cpu")

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


def _resolve_input_device() -> int | str | None:
    """输入设备：env RAPPORT_INPUT_DEVICE > config.json input_device > 系统默认(None)。

    env 仍是字符串（数字串→索引、名字→字符串、空→默认）；config.json 可直接给
    数字（索引）、字符串（名字）或 null（默认）。下次启动生效。
    """
    env_val = os.environ.get(_ENV_PREFIX + "INPUT_DEVICE")
    if env_val is not None:
        return _parse_device(env_val)
    file_val = _load_config_file().get("input_device")
    if file_val is None:
        return None
    if isinstance(file_val, int):
        return file_val
    return _parse_device(str(file_val))


# 录音输入设备：空=系统默认；数字=设备索引；其他=设备名（子串匹配）。
# 用 `rapport devices` 查看可选设备。注意：远程桌面(如 ToDesk)会把虚拟声卡设成默认。
INPUT_DEVICE: int | str | None = _resolve_input_device()

# 语言模型后端 / 模型名 / Ollama 配置：见上方 _DYNAMIC + __getattr__，调用时解析。
# - LLM_PROVIDER：none（默认，未配置）/ fake（看示例）/ anthropic / ollama。
#   配 anthropic 时还需 env ANTHROPIC_API_KEY 或 config.json anthropic_api_key。
# - LLM_MODEL：anthropic 默认 claude-opus-4-8（当前最强 Opus）。
# - OLLAMA_MODEL / OLLAMA_HOST：本地模型默认 qwen2.5:7b、本机 11434。

# 数据目录：开发态默认仓库下 data/；冻结态（PyInstaller 打包后）落到用户级可写目录
# `%LOCALAPPDATA%\Rapport`——装到 Program Files 后目录只读，DB / day-WAV / 状态文件
# 都必须写到用户可写处。基准由 _frozen.data_root() 按冻结标志选取。
# RAPPORT_DATA_DIR 环境变量仍优先覆盖（两态通用）。
DATA_DIR: Path = Path(_env("DATA_DIR", str(_frozen.data_root())))

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
