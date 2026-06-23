"""冻结态路径解析助手 _frozen 与 storage.db schema 定位的单测。

用 monkeypatch 伪造 sys.frozen / sys._MEIPASS，覆盖打包后才走到的分支，
不需要真打包。开发态行为同时验证不变。
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from rapport import _frozen


def test_开发态不算冻结(monkeypatch: pytest.MonkeyPatch) -> None:
    """普通源码态：is_frozen 为假，资源根/数据根落在仓库内。"""
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert _frozen.is_frozen() is False
    # 资源根 = 仓库根（src 的祖父目录），其下有 frontend/。
    assert (_frozen.resource_root() / "src" / "rapport").is_dir()
    # 数据根 = 仓库根下 data/。
    assert _frozen.data_root().name == "data"


def test_冻结态资源根取MEIPASS(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """冻结态：resource_root 返回 sys._MEIPASS。"""
    meipass = tmp_path / "meipass"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    assert _frozen.is_frozen() is True
    assert _frozen.resource_root() == meipass


def test_冻结态数据根取LOCALAPPDATA(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """冻结态：data_root 取 %LOCALAPPDATA%\\Rapport。"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "mei"), raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    assert _frozen.data_root() == tmp_path / "AppData" / "Rapport"


def test_冻结态无LOCALAPPDATA退回家目录(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """冻结态但无 LOCALAPPDATA（异常环境）：退回家目录下 .rapport，不崩。"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "mei"), raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    assert _frozen.data_root() == tmp_path / "home" / ".rapport"


def test_db_schema_冻结态从资源根取(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """冻结态：schema.sql 从 资源根/rapport/storage/schema.sql 取（spec datas 落点）。"""
    from rapport.storage import db as db_mod

    # 在伪造资源根里放一份能建库的 schema.sql。
    real_schema = (
        Path(db_mod.__file__).parent / "schema.sql"
    ).read_text(encoding="utf-8")
    bundled = tmp_path / "rapport" / "storage" / "schema.sql"
    bundled.parent.mkdir(parents=True)
    bundled.write_text(real_schema, encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert db_mod._schema_path() == bundled

    # 用该路径真能建出内存库（executescript 成功）。
    monkeypatch.setattr(db_mod, "_SCHEMA_PATH", db_mod._schema_path())
    conn = db_mod.Database(":memory:")
    try:
        cid = conn.add_conversation(note="冻结态建库")
        assert cid > 0
    finally:
        conn.close()
