"""录制状态文件的原子读写，供 /api/status 诚实读取。

守护进程在状态变化时原子写 `{recording, paused}` 到状态文件；web 后端只读它。
原子写 = 写临时文件再 os.replace 改名，避免读到「写一半」的半截 JSON。
读侧任何异常（文件缺失/损坏/字段缺）都诚实回 `{recording:False, paused:False}`，
绝不抛错——/api/status 不能因状态文件问题返回 500。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# 诚实默认：拿不到可信状态时一律按「未录音」对外。
_DEFAULT = {"recording": False, "paused": False}


def read_status(path: str | Path) -> dict[str, bool]:
    """读状态文件，返回 {recording, paused}；任何异常都回安全默认。

    Args:
        path: 状态文件路径。

    Returns:
        {"recording": bool, "paused": bool}，缺字段补默认。
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return dict(_DEFAULT)
        return {
            "recording": bool(data.get("recording", False)),
            "paused": bool(data.get("paused", False)),
        }
    except (OSError, ValueError):
        # 文件缺失（OSError）或 JSON 损坏（ValueError）都诚实回未录音。
        return dict(_DEFAULT)


def write_status(path: str | Path, *, recording: bool, paused: bool) -> None:
    """原子写状态文件（写临时文件再 os.replace 改名）。

    Args:
        path: 状态文件路径，父目录不存在时自动创建。
        recording: 是否正在录音。
        paused: 是否处于暂停。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".tmp.{os.getpid()}")
    payload = json.dumps(
        {"recording": bool(recording), "paused": bool(paused)},
        ensure_ascii=False,
    )
    try:
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, p)  # 同目录原子改名
    finally:
        # 万一 replace 前出错，清掉临时文件，别留垃圾。
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def clear_status(path: str | Path) -> None:
    """删除状态文件（守护进程退出时调用），幂等：不存在也不抛错。

    Args:
        path: 状态文件路径。
    """
    try:
        Path(path).unlink()
    except OSError:
        pass
