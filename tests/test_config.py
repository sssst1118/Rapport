"""config 纯逻辑测试：默认值与环境变量覆盖（reload 生效）。"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from rapport import config


@pytest.fixture
def 干净环境(monkeypatch: pytest.MonkeyPatch):
    """清除所有 RAPPORT_ 前缀环境变量后 reload config，测后再 reload 复原。"""
    for key in list(__import__("os").environ):
        if key.startswith("RAPPORT_"):
            monkeypatch.delenv(key, raising=False)
    module = importlib.reload(config)
    yield module
    importlib.reload(config)


def test_默认值(干净环境) -> None:
    cfg = 干净环境
    assert cfg.TRANSCRIBER == "local"
    assert cfg.WHISPER_MODEL == "base"
    assert cfg.WHISPER_DEVICE == "cpu"
    assert cfg.WHISPER_COMPUTE_TYPE == "default"
    assert cfg.SAMPLE_RATE == 16000
    assert cfg.CHANNELS == 1
    assert cfg.INPUT_DEVICE is None
    assert isinstance(cfg.DATA_DIR, Path)


def test_环境变量覆盖模型名(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAPPORT_WHISPER_MODEL", "small")
    cfg = importlib.reload(config)
    try:
        assert cfg.WHISPER_MODEL == "small"
    finally:
        monkeypatch.delenv("RAPPORT_WHISPER_MODEL", raising=False)
        importlib.reload(config)


def test_环境变量覆盖数值型(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAPPORT_SAMPLE_RATE", "8000")
    monkeypatch.setenv("RAPPORT_CHANNELS", "2")
    cfg = importlib.reload(config)
    try:
        assert cfg.SAMPLE_RATE == 8000
        assert cfg.CHANNELS == 2
    finally:
        monkeypatch.delenv("RAPPORT_SAMPLE_RATE", raising=False)
        monkeypatch.delenv("RAPPORT_CHANNELS", raising=False)
        importlib.reload(config)


def test_环境变量覆盖数据目录(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RAPPORT_DATA_DIR", str(tmp_path))
    cfg = importlib.reload(config)
    try:
        assert cfg.DATA_DIR == tmp_path
    finally:
        monkeypatch.delenv("RAPPORT_DATA_DIR", raising=False)
        importlib.reload(config)


def test_不支持的transcriber抛错(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAPPORT_TRANSCRIBER", "不存在")
    cfg = importlib.reload(config)
    try:
        with pytest.raises(ValueError):
            cfg.get_transcriber()
    finally:
        monkeypatch.delenv("RAPPORT_TRANSCRIBER", raising=False)
        importlib.reload(config)


def test_输入设备_数字字符串解析为索引(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAPPORT_INPUT_DEVICE", "2")
    cfg = importlib.reload(config)
    try:
        assert cfg.INPUT_DEVICE == 2
        assert isinstance(cfg.INPUT_DEVICE, int)
    finally:
        monkeypatch.delenv("RAPPORT_INPUT_DEVICE", raising=False)
        importlib.reload(config)


def test_输入设备_名字保留为字符串(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAPPORT_INPUT_DEVICE", "Realtek")
    cfg = importlib.reload(config)
    try:
        assert cfg.INPUT_DEVICE == "Realtek"
    finally:
        monkeypatch.delenv("RAPPORT_INPUT_DEVICE", raising=False)
        importlib.reload(config)


# ---- 冻结态（PyInstaller 打包后）路径解析 --------------------------------


def test_开发态数据目录在仓库下data(干净环境) -> None:
    """非冻结（开发）态：DATA_DIR 默认落在仓库根下 data/，行为不变。"""
    cfg = 干净环境
    assert cfg.DATA_DIR.name == "data"
    # DB / 音频 / 状态文件都挂在 DATA_DIR 之下。
    assert cfg.DB_PATH.parent == cfg.DATA_DIR
    assert cfg.AUDIO_DIR.parent == cfg.DATA_DIR
    assert cfg.RECORDING_STATUS_PATH.parent == cfg.DATA_DIR


def test_冻结态数据目录落到LOCALAPPDATA(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """冻结态：DATA_DIR 默认落到 %LOCALAPPDATA%\\Rapport（用户级可写目录）。

    打包装到 Program Files 后目录只读，DB/day-WAV/状态文件必须写用户目录。
    用 monkeypatch 伪造 sys.frozen + sys._MEIPASS + LOCALAPPDATA 验证分支。
    """
    import sys

    # 清掉显式 DATA_DIR 覆盖，确保走默认分支。
    for key in list(__import__("os").environ):
        if key.startswith("RAPPORT_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    try:
        cfg = importlib.reload(config)
        assert cfg.DATA_DIR == tmp_path / "AppData" / "Rapport"
        assert cfg.DB_PATH == cfg.DATA_DIR / "rapport.db"
        assert cfg.AUDIO_DIR == cfg.DATA_DIR / "audio"
    finally:
        importlib.reload(config)


def test_冻结态环境变量仍可覆盖数据目录(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """即便冻结态，RAPPORT_DATA_DIR 显式覆盖仍优先于 LOCALAPPDATA 默认。"""
    import sys

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("RAPPORT_DATA_DIR", str(tmp_path / "custom"))
    try:
        cfg = importlib.reload(config)
        assert cfg.DATA_DIR == tmp_path / "custom"
    finally:
        monkeypatch.delenv("RAPPORT_DATA_DIR", raising=False)
        importlib.reload(config)


# ---- config.json 配置文件层（M5.5 Task 1） ------------------------------
#
# 优先级：环境变量 > config.json > 内置默认。读取每次新鲜（不缓存），
# 文件不存在/坏 JSON 当空配置、绝不崩。LLM 项调用时解析（热生效）。


import json


def _写配置(目录: Path, 内容: dict) -> None:
    """在指定目录写 config.json（测试辅助）。"""
    目录.mkdir(parents=True, exist_ok=True)
    (目录 / "config.json").write_text(
        json.dumps(内容, ensure_ascii=False), encoding="utf-8"
    )


@pytest.fixture
def 隔离数据根(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """把 data_root() 指到 tmp_path，并清空 RAPPORT_ 环境变量，再 reload config。

    这样 config.json 读写都落在临时目录，绝不碰仓库 data/；测后 reload 复原。
    """
    for key in list(__import__("os").environ):
        if key.startswith("RAPPORT_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    module = importlib.reload(config)
    # 防御 monkeypatch×PEP562 的跨测试污染：别的测试用 monkeypatch.setattr(config,
    # "LLM_PROVIDER", ...) 后，undo 会把值「写回」__dict__ 成真实属性（因探测旧值时
    # __getattr__ 响应了），reload 又不清这些非模块体注入的键。此处显式抹掉，确保
    # 这些项重新走 __getattr__ 动态解析。
    for 动态键 in module._DYNAMIC:
        module.__dict__.pop(动态键, None)
    monkeypatch.setattr(module._frozen, "data_root", lambda: tmp_path)
    yield module, tmp_path
    importlib.reload(config)


def test_load_config_file_缺失返回空(隔离数据根) -> None:
    """data_root 下无 config.json → 返回 {}，不抛。"""
    cfg, _ = 隔离数据根
    assert cfg._load_config_file() == {}


def test_load_config_file_坏json返回空(隔离数据根) -> None:
    """config.json 是坏 JSON → 当空配置返回 {}，绝不崩。"""
    cfg, root = 隔离数据根
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.json").write_text("{ 这不是合法 JSON ", encoding="utf-8")
    assert cfg._load_config_file() == {}


def test_load_config_file_合法读回(隔离数据根) -> None:
    """合法 config.json → 原样返回 dict。"""
    cfg, root = 隔离数据根
    _写配置(root, {"llm_provider": "ollama", "llm_model": "qwen2.5:7b-instruct"})
    assert cfg._load_config_file() == {
        "llm_provider": "ollama",
        "llm_model": "qwen2.5:7b-instruct",
    }


def test_setting_默认_无env无file(隔离数据根) -> None:
    """env 与 file 都没有该项 → 取默认。"""
    cfg, _ = 隔离数据根
    assert cfg._setting("WHISPER_MODEL", "whisper_model", "base") == "base"


def test_setting_file覆盖默认(隔离数据根) -> None:
    """file 有该项、env 没有 → file 赢过默认。"""
    cfg, root = 隔离数据根
    _写配置(root, {"whisper_model": "small"})
    assert cfg._setting("WHISPER_MODEL", "whisper_model", "base") == "small"


def test_setting_env覆盖file(隔离数据根, monkeypatch: pytest.MonkeyPatch) -> None:
    """env 与 file 都有 → env 赢（最高优先级）。"""
    cfg, root = 隔离数据根
    _写配置(root, {"whisper_model": "small"})
    monkeypatch.setenv("RAPPORT_WHISPER_MODEL", "medium")
    assert cfg._setting("WHISPER_MODEL", "whisper_model", "base") == "medium"


def test_setting_file值为null当作未设(隔离数据根) -> None:
    """config.json 里某键显式 null → 视为未设，回退默认。"""
    cfg, root = 隔离数据根
    _写配置(root, {"whisper_model": None})
    assert cfg._setting("WHISPER_MODEL", "whisper_model", "base") == "base"


def test_llm_provider_跟随config_json热生效(隔离数据根) -> None:
    """config.json 设 llm_provider → config.LLM_PROVIDER 调用时取到（无需重启）。

    隔离数据根已 reload 过 config（import 期 LLM_PROVIDER 未定为常量），
    此处不再 reload，直接访问属性即应反映 config.json，证明调用时解析。
    """
    cfg, root = 隔离数据根
    _写配置(root, {"llm_provider": "fake"})
    assert cfg.LLM_PROVIDER == "fake"
    # 改文件后再次访问应立即跟随（热生效，不缓存、不 reload）。
    _写配置(root, {"llm_provider": "ollama"})
    assert cfg.LLM_PROVIDER == "ollama"


def test_llm_provider_默认none(隔离数据根) -> None:
    """无 env 无 file → LLM_PROVIDER 默认 none（行为与改前一致）。"""
    cfg, _ = 隔离数据根
    assert cfg.LLM_PROVIDER == "none"


def test_llm_provider_env赢config(隔离数据根, monkeypatch: pytest.MonkeyPatch) -> None:
    """env RAPPORT_LLM_PROVIDER 与 config.json 同设 → env 赢。"""
    cfg, root = 隔离数据根
    _写配置(root, {"llm_provider": "fake"})
    monkeypatch.setenv("RAPPORT_LLM_PROVIDER", "none")
    assert cfg.LLM_PROVIDER == "none"


def test_llm_model_跟随config_json(隔离数据根) -> None:
    """config.json 设 llm_model → config.LLM_MODEL 取到。"""
    cfg, root = 隔离数据根
    _写配置(root, {"llm_model": "claude-haiku-4-5"})
    assert cfg.LLM_MODEL == "claude-haiku-4-5"


def test_get_provider_跟随config_json(隔离数据根) -> None:
    """端到端：config.json 设 fake → analysis.get_provider() 返回 FakeProvider。

    证明 LLM provider 在「调用时」解析，改 config.json 无需重启即生效。
    """
    cfg, root = 隔离数据根
    _写配置(root, {"llm_provider": "fake"})
    from rapport.analysis import get_provider
    from rapport.analysis.llm.fake_provider import FakeProvider

    assert isinstance(get_provider(), FakeProvider)


def test_anthropic_api_key_读裸env(隔离数据根, monkeypatch: pytest.MonkeyPatch) -> None:
    """裸环境变量 ANTHROPIC_API_KEY（无 RAPPORT_ 前缀）最高优先。"""
    cfg, root = 隔离数据根
    _写配置(root, {"anthropic_api_key": "sk-ant-from-file"})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")
    assert cfg.anthropic_api_key() == "sk-ant-from-env"


def test_anthropic_api_key_读config_json(隔离数据根) -> None:
    """无 env 时从 config.json 的 anthropic_api_key 取。"""
    cfg, root = 隔离数据根
    _写配置(root, {"anthropic_api_key": "sk-ant-from-file"})
    assert cfg.anthropic_api_key() == "sk-ant-from-file"


def test_anthropic_api_key_都没有返回none(隔离数据根) -> None:
    """env 与 file 都没有 → None（让 SDK 自行报缺 key）。"""
    cfg, _ = 隔离数据根
    assert cfg.anthropic_api_key() is None


def test_save_config_写后读回(隔离数据根) -> None:
    """save_config 写入后，_load_config_file 读回值正确。"""
    cfg, _ = 隔离数据根
    cfg.save_config({"llm_provider": "ollama"})
    assert cfg._load_config_file()["llm_provider"] == "ollama"


def test_save_config_合并不丢旧键(隔离数据根) -> None:
    """二次 save 只合并传入键，不清空之前写的键。"""
    cfg, _ = 隔离数据根
    cfg.save_config({"llm_provider": "ollama"})
    cfg.save_config({"llm_model": "qwen2.5:7b-instruct"})
    data = cfg._load_config_file()
    assert data["llm_provider"] == "ollama"
    assert data["llm_model"] == "qwen2.5:7b-instruct"


def test_save_config_目录不存在自动建(隔离数据根) -> None:
    """data_root 目录尚不存在时，save_config 先建目录再写。"""
    cfg, root = 隔离数据根
    深目录 = root / "不存在" / "更深"
    import rapport._frozen as _frozen

    # 把 data_root 指到一个尚未创建的深目录
    import pytest as _pytest

    mp = _pytest.MonkeyPatch()
    mp.setattr(_frozen, "data_root", lambda: 深目录)
    try:
        assert not 深目录.exists()
        cfg.save_config({"llm_provider": "fake"})
        assert (深目录 / "config.json").exists()
    finally:
        mp.undo()


def test_save_config_原子不留临时文件(隔离数据根) -> None:
    """save_config 用临时文件+replace，落定后目录里不残留临时文件。"""
    cfg, root = 隔离数据根
    cfg.save_config({"llm_provider": "fake"})
    残留 = [p.name for p in root.iterdir() if p.name != "config.json"]
    assert 残留 == []


def test_anthropic_provider_把config_json的key传进sdk(
    隔离数据根, monkeypatch: pytest.MonkeyPatch
) -> None:
    """env 无 key、config.json 有 → AnthropicProvider 调用时把该 key 传给 SDK。

    用假的 anthropic 模块注入 sys.modules，捕获 Anthropic(api_key=...) 的实参，
    证明 config.json 的 anthropic_api_key 真正被消费（不靠 SDK 自动读 env）。
    不联网。
    """
    import sys
    import types

    cfg, root = 隔离数据根
    _写配置(root, {"anthropic_api_key": "sk-ant-from-file"})

    捕获: dict = {}

    class _FakeMessages:
        def create(self, **kwargs):
            raise RuntimeError("不该真的调用网络")

    class _FakeAnthropic:
        def __init__(self, *args, **kwargs):
            捕获["api_key"] = kwargs.get("api_key")
            self.messages = _FakeMessages()

    class _FakeAPIError(Exception):
        pass

    假模块 = types.ModuleType("anthropic")
    假模块.Anthropic = _FakeAnthropic
    假模块.APIError = _FakeAPIError
    monkeypatch.setitem(sys.modules, "anthropic", 假模块)

    from rapport.analysis.llm.anthropic_provider import AnthropicProvider

    provider = AnthropicProvider()
    # generate_json 会构造 client（捕获 api_key），随后 _FakeMessages.create 抛错
    # 被包成 AnalysisError——我们只关心 client 拿到的 key。
    with pytest.raises(Exception):
        provider.generate_json("sys", "user", {"type": "object"})
    assert 捕获["api_key"] == "sk-ant-from-file"
