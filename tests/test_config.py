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
