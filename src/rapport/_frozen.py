r"""冻结态（PyInstaller 打包后）路径解析的统一助手。

开发态（直接从源码树跑）与冻结态（`rapport app` 被 PyInstaller 打成 onedir 后跑）
对「资源在哪」「可写数据落哪」的答案完全不同，本模块把这两类路径集中到一处，
让 config / web / storage 各自从这里取，避免散落的 `parents[N]` 在冻结后失效。

两个根的区别：
- **资源根 resource_root()**：只读的随包资源（frontend/dist、schema.sql）所在基准。
  - 开发态 = 仓库根（本文件位于 src/rapport/_frozen.py，上溯三级）。
  - 冻结态 = `sys._MEIPASS`（PyInstaller 解包出来的 bundle 临时目录，datas 落于此）。
- **数据根 data_root()**：可写的用户数据（DB、day-WAV、状态文件）所在基准。
  - 开发态 = 仓库根下 data/（保持原行为，现有测试不变）。
  - 冻结态 = `%LOCALAPPDATA%\Rapport`（装到 Program Files 后目录只读，必须写用户级目录）。

判定：`getattr(sys, "frozen", False)` 为 PyInstaller 设置的标志；`sys._MEIPASS` 为
解包目录。两者都满足才算冻结态。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 仓库根：本文件位于 src/rapport/_frozen.py，上溯三级父目录到仓库根。
_REPO_ROOT = Path(__file__).resolve().parents[2]


def is_frozen() -> bool:
    """是否运行在 PyInstaller 冻结态（已打包）。"""
    return bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))


def resource_root() -> Path:
    """只读随包资源（frontend/dist、schema.sql）的基准目录。

    冻结态取 `sys._MEIPASS`（PyInstaller datas 解包于此）；开发态取仓库根。
    """
    if is_frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return _REPO_ROOT


def data_root() -> Path:
    r"""可写用户数据（DB、day-WAV、状态文件）的基准目录。

    冻结态取用户级可写目录 ``%LOCALAPPDATA%\Rapport``（Windows）/ 退而求其次用
    家目录下 .rapport；开发态取仓库根下 data/（保持原行为）。

    注：仅返回路径，不创建目录——各写入方（write_status / DayWavWriter / sqlite）
    自行按需 mkdir，与原行为一致。
    """
    if is_frozen():
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "Rapport"
        return Path.home() / ".rapport"
    return _REPO_ROOT / "data"
