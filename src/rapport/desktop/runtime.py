"""编排层：构造真实依赖（Engine + uvicorn serve + 浏览器回调），组装并运行托盘应用。

`rapport app` 的落点。单进程内：
- uvicorn serve 跑在后台守护线程（uvicorn.Server + should_exit 优雅启停）；
- 常驻 Engine（复用 alwayson.engine.Engine + MicAudioSource）跑在它自己的音频回调线程；
- pystray 的 icon.run() 占主线程（Windows 上最稳）；
- 一个轻量状态轮询线程，把 Engine 内存状态变化（暂停/恢复/停止）刷到托盘图标。

重依赖（pystray/uvicorn/sounddevice/faster-whisper/fastapi）全部在本模块函数内延迟导入，
保持与其他子命令一致的风格：未装 GUI 依赖时其余命令不受影响。controller.py 仍纯净。
"""

from __future__ import annotations

import threading
import webbrowser
from pathlib import Path

from .controller import AppController


class _UvicornServeHandle:
    """uvicorn.Server 的薄包装：后台线程跑 server.run()，stop() 设 should_exit 优雅关闭。

    符合 controller 期望的 serve 句柄契约（只需有 stop()）。
    """

    def __init__(self, app, *, host: str, port: int) -> None:  # noqa: ANN001
        import uvicorn  # 延迟导入

        config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run, daemon=True, name="rapport-uvicorn"
        )

    def start(self) -> None:
        """后台守护线程启动 uvicorn 事件循环。"""
        self._thread.start()

    def wait_started(self, timeout: float = 10.0) -> bool:
        """等 uvicorn 进入 serving 状态（server.started 置位）。返回是否在超时内起来。"""
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if getattr(self._server, "started", False):
                return True
            time.sleep(0.05)
        return getattr(self._server, "started", False)

    def stop(self) -> None:
        """触发 uvicorn 优雅关闭（设 should_exit），并等后台线程收尾。幂等。"""
        self._server.should_exit = True
        thread = self._thread
        if thread.is_alive():
            thread.join(timeout=5.0)


def _build_engine(device_raw: str | None):  # noqa: ANN201
    """照 __main__._cmd_watch 的方式构造真实 Engine（麦克风源 + 转写 + 分离 + DB）。"""
    from .. import config
    from ..alwayson.engine import Engine
    from ..alwayson.mic import MicAudioSource
    from ..diarize import get_diarizer
    from ..storage.db import Database

    device = config._parse_device(device_raw) if device_raw else config.INPUT_DEVICE
    # 守护进程独占一条 DB 连接；音频回调在 sounddevice 自己的线程里，故放宽跨线程检查。
    db = Database(config.DB_PATH, check_same_thread=False)
    transcriber = config.get_transcriber()
    diarizer = get_diarizer()
    source = MicAudioSource(
        samplerate=config.SAMPLE_RATE, channels=config.CHANNELS, device=device
    )
    engine = Engine(db, transcriber, diarizer, source)
    return engine, db


def _build_app(repo_root: Path):  # noqa: ANN201
    """构造与 serve 子命令一致的 FastAPI 应用（复用 create_app 默认 db_path/status_path）。"""
    from ..web import create_app

    return create_app(repo_root=repo_root)


def _poll_loop(icon, controller: AppController, stop_event: threading.Event) -> None:  # noqa: ANN001
    """状态轮询线程：Engine 状态变化时把图标/tooltip/菜单刷新到托盘。"""
    from . import tray

    last = None
    while not stop_event.is_set():
        state = controller.icon_state()
        if state != last:
            last = state
            tray.refresh(icon, controller)
        if controller.should_exit:
            try:
                icon.stop()
            except Exception:  # noqa: BLE001
                pass
            return
        stop_event.wait(0.3)


def _should_open_on_launch(open_ui: bool) -> bool:
    """启动时是否自动用浏览器打开界面。

    单独抽成纯函数便于单测（run_app 整体跑真 tray 难单测）：open_ui 即结果，
    默认 True（双击打包应用立刻可见界面、不再「隐形」），--no-open 传 False 关掉。
    """
    return bool(open_ui)


def run_app(
    *,
    port: int = 8000,
    host: str = "127.0.0.1",
    device: str | None = None,
    record: bool = True,
    open_ui: bool = True,
) -> int:
    """启动桌面托盘应用：serve（后台线程）+ Engine + 托盘图标（主线程 icon.run()）。

    Args:
        port: web 界面端口（默认 8000）。
        host: 监听地址（默认 127.0.0.1，本地优先）。
        device: 录音输入设备（索引/名称/None=配置默认）。
        record: 启动即录音（always-on 本色）；False 则起来先不录（--no-record，调试/隐私）。
        open_ui: 启动后自动用默认浏览器打开界面（默认 True，解决「启动隐形」）；
            False（--no-open）则不弹浏览器（不想自动弹 / 将来开机自启场景）。

    Returns:
        进程退出码（正常 0）。
    """
    from .._frozen import data_root
    from . import tray

    # audio_path 的可写基准：冻结态 = %LOCALAPPDATA%\Rapport（与 config.AUDIO_DIR/
    # DB 同根），开发态 = 仓库根。前端 dist 由 create_app 自行从资源根取，不受此影响。
    repo_root = data_root()
    url = f"http://{host}:{port}"

    # 1) 后台起 uvicorn serve（与 rapport serve 同款 app）。
    app = _build_app(repo_root)
    serve = _UvicornServeHandle(app, host=host, port=port)
    serve.start()
    serve.wait_started()

    # 2) 构造常驻 Engine；按 record 决定是否启动即录音。
    engine, db = _build_engine(device)
    if record:
        engine.start()

    # 3) 组装控制器（图标/菜单读 Engine 内存状态；open_ui 用默认浏览器开 url）。
    controller = AppController(
        engine, serve, lambda: webbrowser.open(url), url=url
    )

    # 4) 真实托盘图标 + 状态轮询线程，icon.run() 占主线程。
    icon = tray.build_icon(controller)
    stop_event = threading.Event()
    poller = threading.Thread(
        target=_poll_loop,
        args=(icon, controller, stop_event),
        daemon=True,
        name="rapport-tray-poll",
    )
    poller.start()

    print(f"● Rapport 桌面应用已启动：{url}", flush=True)
    if record:
        print("● 正在录音（托盘图标红点）。可在托盘菜单暂停/退出。", flush=True)
    else:
        print("○ 未自动录音（--no-record）。可在托盘菜单开始（暂停/继续）/退出。", flush=True)

    # 启动可见：serve 已 started，自动用默认浏览器打开界面，用户立刻看到 Rapport、
    # 不再「双击后什么都没有」。--no-open 时跳过（_should_open_on_launch 返回 False）。
    if _should_open_on_launch(open_ui):
        webbrowser.open(url)
        print(f"● 界面已在浏览器打开：{url}", flush=True)

    try:
        icon.run()  # 阻塞，直到 on_quit → should_exit → poller 调 icon.stop()
    finally:
        stop_event.set()
        # 兜底优雅收尾（on_quit 幂等，重复调安全）：停 Engine、停 serve、关 DB。
        controller.on_quit()
        try:
            db.close()
        except Exception:  # noqa: BLE001
            pass
        # 保底强制终止：windowed 打包应用必须保证「退出」即死。即便 PortAudio/uvicorn
        # 仍残留非守护线程（icon.run() 返回后它们可能让进程不退），os._exit(0) 直接结束
        # 进程，用户点「退出」一定关得掉。必须放在上面所有清理之后——os._exit 跳过
        # atexit / 缓冲刷新，此刻 DB、状态文件、serve 都已收尾，强杀是安全的。
        import os

        os._exit(0)
    return 0  # 不可达（os._exit 已终止）；保留以满足类型签名 -> int
