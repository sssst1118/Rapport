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
