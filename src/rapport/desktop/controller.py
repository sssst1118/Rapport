"""桌面托盘的纯逻辑核心：AppController。

把「菜单/状态逻辑」与「真实 pystray / uvicorn / 麦克风」彻底分开：本模块**顶部不
导入 pystray / uvicorn / sounddevice / PIL**，只依赖被注入对象的鸭子接口，因而能用
假对象确定性单测，不需要显示器/声卡/网络。tray.py / runtime.py 负责把真实依赖接上。

注入三件套：
- recorder：有 start()/pause()/resume()/stop() 和可读 recording/paused 状态的对象
  （真实=alwayson.Engine；测试=假对象）。
- serve_handle：有 stop() 的句柄（真实=uvicorn server 的包装；测试=假对象）。
- open_url：无参回调，打开界面（真实=webbrowser.open(url) 的偏函数；测试=记录式）。

状态来源：图标/菜单直接读 recorder 的内存状态（同进程，最简单可靠）；serve 的
/api/status 仍读状态文件（Engine 已写），两边一致。
"""

from __future__ import annotations

from typing import Any, Callable, Protocol


class _Recorder(Protocol):
    """录音器契约（真实=Engine，测试=假对象）。"""

    recording: bool
    paused: bool

    def start(self) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def stop(self) -> None: ...


class _ServeHandle(Protocol):
    """serve 句柄契约：只需可停。"""

    def stop(self) -> None: ...


class AppController:
    """托盘应用的逻辑核心：菜单动作 + 图标状态，全部从注入对象推出。"""

    def __init__(
        self,
        recorder: _Recorder,
        serve_handle: _ServeHandle,
        open_url: Callable[[], None],
        *,
        url: str,
    ) -> None:
        """构造控制器。

        Args:
            recorder: 录音器（真实 Engine 或假对象），暴露 recording/paused 与生命周期方法。
            serve_handle: 有 stop() 的 serve 句柄（真实 uvicorn 包装或假对象）。
            open_url: 无参回调，调用即打开界面（真实 webbrowser.open，测试记录式）。
            url: 界面地址，仅用于展示/记录（实际打开动作封装在 open_url 里）。
        """
        self._recorder = recorder
        self._serve = serve_handle
        self._open_url = open_url
        self.url = url
        # 退出标志：on_quit 置位后，tray 主循环据此 icon.stop()。
        self.should_exit = False
        # 幂等护栏：on_quit 只真正停一次 recorder/serve。
        self._quit_done = False

    # ---- 图标状态 / tooltip --------------------------------------------

    def icon_state(self) -> str:
        """由 recorder 状态推出图标三态：recording / paused / idle。"""
        if not self._recorder.recording:
            return "idle"
        if self._recorder.paused:
            return "paused"
        return "recording"

    def tooltip(self) -> str:
        """跟随图标状态的中文 tooltip 文案（持续可见的录制指示）。"""
        state = self.icon_state()
        if state == "recording":
            return "Rapport · ● 正在录音"
        if state == "paused":
            return "Rapport · ⏸ 已暂停"
        return "Rapport · ○ 未录音"

    # ---- 菜单动作 ------------------------------------------------------

    def on_toggle_pause(self) -> None:
        """切换录音状态：未录音→start()，录音中→pause()，已暂停→resume()。

        让托盘从空闲态（如 --no-record 启动、或 stop 之后）也能一键开始采集，
        而不只是在「录音中」与「暂停」之间切。
        """
        if not self._recorder.recording:
            self._recorder.start()
        elif self._recorder.paused:
            self._recorder.resume()
        else:
            self._recorder.pause()

    def on_open_ui(self) -> None:
        """打开界面：调注入的 open_url 回调（真实=默认浏览器开 url）。"""
        self._open_url()

    def on_quit(self) -> None:
        """优雅退出：按序停 recorder → serve，并置退出标志。幂等、可重复调不抛。

        recorder.stop() 收尾当天 day-WAV、清状态文件（见 Engine.stop）；
        serve.stop() 触发 uvicorn 优雅关闭。两者各包 try，确保即便一个抛了另一个仍执行、
        退出标志仍置位（tray 主循环才能停下）。
        """
        if not self._quit_done:
            self._quit_done = True
            try:
                self._recorder.stop()
            except Exception:  # noqa: BLE001 - 退出收尾尽力而为，不让异常卡住关闭
                pass
            try:
                self._serve.stop()
            except Exception:  # noqa: BLE001
                pass
        self.should_exit = True

    # ---- 菜单描述（供 tray.py 构造真实 pystray.Menu） ------------------

    def _toggle_label(self) -> str:
        """toggle 项的当前文案：录音中→「暂停录音」，已暂停→「继续录音」，空闲→「开始录音」。"""
        state = self.icon_state()
        if state == "recording":
            return "暂停录音"
        if state == "paused":
            return "继续录音"
        return "开始录音"

    def menu_items(self) -> list[dict[str, Any]]:
        """结构化菜单描述（label + 动作键），便于 tray 构造真实菜单、也便于单测文案。

        每项：{"key": 动作键, "label": 显示文案}。动作键映射到本类方法：
        toggle_pause→on_toggle_pause，open_ui→on_open_ui，quit→on_quit。
        """
        return [
            {"key": "toggle_pause", "label": self._toggle_label()},
            {"key": "open_ui", "label": "打开界面"},
            {"key": "quit", "label": "退出"},
        ]
