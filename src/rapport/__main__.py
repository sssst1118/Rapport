"""Rapport 命令行入口。

子命令：
    rapport ui                       启动 Gradio 界面。
    rapport transcribe FILE          转写音频文件并打印文本。
    rapport record FILE [--seconds N] 录音保存到 FILE。
    rapport ingest FILE [--note N]   转写+分离并入库。
    rapport show CONV_ID             打印某对话的全部话语。
    rapport search QUERY             全文检索话语。
    rapport serve [--port 8000]      启动 FastAPI Web 后端。
    rapport mcp                      以 stdio 启动 MCP server（暴露只读数据工具给 AI 助手）。

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
    --device 可指定输入设备（索引或名称），不指定则用配置默认。
    """
    from . import config
    from .audio.recorder import Recorder, record_to_wav

    device = config._parse_device(args.device) if args.device else config.INPUT_DEVICE

    if args.seconds is not None:
        record_to_wav(args.file, args.seconds, device=device)
    else:
        recorder = Recorder(device=device)
        recorder.start()
        try:
            input("按回车停止录音…")
        finally:
            recorder.stop(args.file)
    print(f"已保存录音：{args.file}")
    return 0


def _cmd_devices(args: argparse.Namespace) -> int:
    """列出可用录音输入设备。"""
    from . import config
    from .audio.recorder import list_input_devices

    print("可用录音输入设备（索引  名称）：")
    for idx, name in list_input_devices():
        print(f"  {idx:3d}  {name}")
    current = config.INPUT_DEVICE if config.INPUT_DEVICE is not None else "系统默认"
    print(f"\n当前选用：{current}")
    print("用法：rapport record out.wav --seconds 5 --device 2  （--device 也可填设备名）")
    print("或设环境变量：RAPPORT_INPUT_DEVICE=2")
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    """转写+说话人分离一段音频并写入数据库。"""
    from . import config
    from .ingest import ingest_audio
    from .storage.db import Database

    db = Database(config.DB_PATH)
    try:
        cid = ingest_audio(args.file, db, note=args.note)
        n = len(db.get_utterances(cid))
    finally:
        db.close()
    print(f"对话 #{cid}，入库 {n} 句")
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    """打印某对话下的全部话语（说话人标签 + 文本）。"""
    from . import config
    from .storage.db import Database

    db = Database(config.DB_PATH)
    try:
        rows = db.get_utterances(args.conv_id)
    finally:
        db.close()
    for row in rows:
        label = row["speaker_label"] or "?"
        print(f"[{label}] {row['text']}")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    """全文检索话语并打印命中结果。"""
    from . import config
    from .storage.db import Database

    db = Database(config.DB_PATH)
    try:
        rows = db.search_utterances(args.query)
    finally:
        db.close()
    for row in rows:
        label = row["speaker_label"] or "?"
        print(f"对话 #{row['conversation_id']} [{label}] {row['text']}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """启动 FastAPI Web 后端（uvicorn）。

    重依赖（fastapi/uvicorn）在此延迟导入，保持与其他子命令一致的风格。
    --reload 时必须用 import string 让 uvicorn 接管重载，否则传 app 实例直接起。
    """
    import uvicorn

    if args.reload:
        # reload 模式必须给 uvicorn 一个 import string；用 --factory 指向应用工厂，
        # 既能让子进程重新导入，又避开「子模块名 app 遮蔽默认实例」的坑。
        uvicorn.run(
            "rapport.web:create_app",
            host=args.host,
            port=args.port,
            reload=True,
            factory=True,
        )
    else:
        from .web import create_app

        uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


def _cmd_mcp(args: argparse.Namespace) -> int:
    """以 stdio 启动 MCP server，把本地只读数据做成工具暴露给 AI 助手。

    mcp SDK 在此延迟导入，保持与其他子命令一致的风格（未装 mcp 时其余命令不受影响）。
    """
    from .mcp import server

    server.run()
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
        help="录音时长（秒）；不指定则手动开关（按回车停止）",
    )
    p_rec.add_argument(
        "--device",
        default=None,
        help="输入设备索引或名称（默认配置/系统默认；见 rapport devices）",
    )
    p_rec.set_defaults(func=_cmd_record)

    p_dev = subparsers.add_parser("devices", help="列出可用录音输入设备")
    p_dev.set_defaults(func=_cmd_devices)

    p_ing = subparsers.add_parser("ingest", help="转写+分离并入库")
    p_ing.add_argument("file", help="音频文件路径")
    p_ing.add_argument("--note", default=None, help="对话备注")
    p_ing.set_defaults(func=_cmd_ingest)

    p_show = subparsers.add_parser("show", help="打印某对话的全部话语")
    p_show.add_argument("conv_id", type=int, help="对话 id")
    p_show.set_defaults(func=_cmd_show)

    p_search = subparsers.add_parser("search", help="全文检索话语")
    p_search.add_argument("query", help="检索词")
    p_search.set_defaults(func=_cmd_search)

    p_serve = subparsers.add_parser("serve", help="启动 FastAPI Web 后端")
    p_serve.add_argument("--port", type=int, default=8000, help="监听端口（默认 8000）")
    p_serve.add_argument(
        "--host", default="127.0.0.1", help="监听地址（默认 127.0.0.1）"
    )
    p_serve.add_argument(
        "--reload", action="store_true", help="开发模式：代码改动自动重载"
    )
    p_serve.set_defaults(func=_cmd_serve)

    p_mcp = subparsers.add_parser(
        "mcp", help="以 stdio 启动 MCP server（暴露只读数据工具给 AI 助手）"
    )
    p_mcp.set_defaults(func=_cmd_mcp)

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
