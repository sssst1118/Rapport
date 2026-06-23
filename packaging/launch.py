"""PyInstaller 打包入口：等价于 `rapport app`（托盘 + serve + 常驻录音）。

PyInstaller 以本脚本为 onedir 产物的入口。直接调用 desktop.runtime.run_app，
等价于命令行 `rapport app` 的默认参数（端口 8000、127.0.0.1、启动即录音）。

为什么不直接用 `rapport.__main__:main`：打包入口要稳定、参数固定，避免依赖
argparse 解析 sys.argv（双击启动时 sys.argv 只有 exe 路径）；同时显式只拉
desktop 这条重依赖链，语义清晰。
"""

from __future__ import annotations

import sys


def _main() -> int:
    # stdout/stderr 切 UTF-8（与 __main__.main 一致），windowed 模式下二者可能为 None。
    from rapport.__main__ import _force_utf8_stdout

    _force_utf8_stdout()

    from rapport.desktop.runtime import run_app

    return run_app(port=8000, host="127.0.0.1", device=None, record=True)


if __name__ == "__main__":
    sys.exit(_main())
