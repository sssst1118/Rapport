"""PyInstaller 打包入口：等价于 `rapport app`（托盘 + serve + 常驻录音）。

PyInstaller 以本脚本为 onedir 产物的入口。直接调用 desktop.runtime.run_app，
等价于命令行 `rapport app` 的默认参数（端口 8000、127.0.0.1、启动即录音）。

为什么不直接用 `rapport.__main__:main`：打包入口要稳定、参数固定，避免依赖
argparse 解析 sys.argv（双击启动时 sys.argv 只有 exe 路径）；同时显式只拉
desktop 这条重依赖链，语义清晰。
"""

from __future__ import annotations

import sys


def _ensure_streams() -> None:
    """windowed（无控制台）模式下 sys.stdout/stderr 为 None：uvicorn 配置日志时会对其
    调 isatty() 而崩（'NoneType' object has no attribute 'isatty'），run_app 的 print
    也会因 None 而崩。把 None 的流重定向到用户数据目录的 rapport.log（行缓冲、utf-8），
    既消除崩溃又留运行日志；连日志文件都开不了时退回 devnull，确保流非 None。"""
    if sys.stdout is not None and sys.stderr is not None:
        return
    stream = None
    try:
        from rapport._frozen import data_root

        log_dir = data_root()
        log_dir.mkdir(parents=True, exist_ok=True)
        stream = open(log_dir / "rapport.log", "a", encoding="utf-8", buffering=1)
    except Exception:
        try:
            import io
            import os

            stream = io.TextIOWrapper(open(os.devnull, "wb"), encoding="utf-8")
        except Exception:
            return
    if sys.stdout is None:
        sys.stdout = stream
    if sys.stderr is None:
        sys.stderr = stream


def _main() -> int:
    # windowed 模式先把 None 的 stdout/stderr 接到 rapport.log，否则 uvicorn 日志配置的
    # isatty() 与 run_app 的 print 都会因 None 崩溃（exitcode=1 静默闪退）。
    _ensure_streams()

    # stdout/stderr 切 UTF-8（与 __main__.main 一致）。
    from rapport.__main__ import _force_utf8_stdout

    _force_utf8_stdout()

    from rapport.desktop.runtime import run_app

    return run_app(port=8000, host="127.0.0.1", device=None, record=True)


def _log_crash(exc: BaseException) -> None:
    """windowed 模式无控制台，主线程未捕获异常会静默退出（exitcode=1）看不到任何线索。
    把完整 traceback 落到用户数据目录的 crash.log，既方便开发排查，也是给最终用户的
    崩溃线索（"应用闪退"时有据可查）。尽力而为，写日志本身再抛就忽略。"""
    import traceback

    try:
        from rapport._frozen import data_root

        log_dir = data_root()
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "crash.log", "a", encoding="utf-8") as f:
            f.write("=== Rapport 崩溃 ===\n")
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
            f.write("\n")
    except Exception:
        pass


if __name__ == "__main__":
    try:
        sys.exit(_main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001 - 顶层兜底：记录任何崩溃再退出
        _log_crash(exc)
        sys.exit(1)
