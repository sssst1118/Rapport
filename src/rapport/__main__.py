"""Rapport 命令行入口。

子命令：
    rapport ui                       启动 Gradio 界面。
    rapport transcribe FILE          转写音频文件并打印文本。
    rapport record FILE [--seconds N] 录音保存到 FILE。

入口函数 main 供 [project.scripts] 的 rapport=rapport.__main__:main 调用。
重依赖（gradio / sounddevice / faster-whisper）均在各子命令内延迟触发。
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def _cmd_ui(args: argparse.Namespace) -> int:
    """启动 Gradio 界面。"""
    from .ui import app

    launch_kwargs: dict[str, object] = {}
    if args.share:
        launch_kwargs["share"] = True
    if args.port is not None:
        launch_kwargs["server_port"] = args.port
    app.launch(**launch_kwargs)
    return 0


def _cmd_transcribe(args: argparse.Namespace) -> int:
    """转写单个音频文件并打印结果文本。"""
    from . import config
    from .transcribe.text import segments_to_text

    transcriber = config.get_transcriber()
    segments = transcriber.transcribe(args.file)
    print(segments_to_text(segments))
    return 0


def _cmd_record(args: argparse.Namespace) -> int:
    """录音并保存到指定 WAV 文件。

    指定 --seconds 时录制固定时长；否则手动开关：按回车停止。
    """
    from .audio.recorder import Recorder, record_to_wav

    if args.seconds is not None:
        record_to_wav(args.file, args.seconds)
    else:
        recorder = Recorder()
        recorder.start()
        try:
            input("按回车停止录音…")
        finally:
            recorder.stop(args.file)
    print(f"已保存录音：{args.file}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="rapport",
        description="Rapport：本地优先的人际对话助手。",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_ui = subparsers.add_parser("ui", help="启动 Gradio 界面")
    p_ui.add_argument("--port", type=int, default=None, help="监听端口")
    p_ui.add_argument("--share", action="store_true", help="生成公网分享链接")
    p_ui.set_defaults(func=_cmd_ui)

    p_tr = subparsers.add_parser("transcribe", help="转写音频文件并打印文本")
    p_tr.add_argument("file", help="音频文件路径")
    p_tr.set_defaults(func=_cmd_transcribe)

    p_rec = subparsers.add_parser("record", help="录音保存到文件")
    p_rec.add_argument("file", help="输出 WAV 文件路径")
    p_rec.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="录音时长（秒）；不指定时由录音实现决定其默认行为",
    )
    p_rec.set_defaults(func=_cmd_record)

    return parser


def _force_utf8_stdout() -> None:
    """Windows 控制台默认 GBK，非 GBK 字符（如 emoji）会让 print 崩溃；
    尽力把 stdout/stderr 切到 UTF-8 以避免之。"""
    import sys

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass


def main(argv: Sequence[str] | None = None) -> int:
    """命令行入口。

    Args:
        argv: 参数列表，None 时使用 sys.argv。

    Returns:
        进程退出码。
    """
    _force_utf8_stdout()
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
