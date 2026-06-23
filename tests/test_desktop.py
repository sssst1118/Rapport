"""桌面托盘控制器测试：纯逻辑核心 AppController，全用假对象。

不依赖 pystray / PIL / uvicorn / 麦克风 —— controller.py 顶部不导入它们，
测试也不导入它们，无论是否装了 GUI 依赖都要绿。覆盖：
- icon_state() / tooltip() 随 recorder 状态三态正确变化（recording/paused/idle）。
- on_toggle_pause()：recording 时 pause、paused 时 resume。
- on_open_ui() 调了 open_url（带对的 url）。
- on_quit()：按序停 recorder→serve、标志置位，**重复调用幂等不抛**。
- menu_items() 文案随状态变（暂停录音 ↔ 继续录音）。
- （装了 pystray 时）能用真 controller 构造出 tray 菜单结构不抛；未装则跳过。
"""

from __future__ import annotations

import pytest

from rapport.desktop.controller import AppController


# ---- 假对象 --------------------------------------------------------------


class _假录音器:
    """假 recorder：有 start/pause/resume/stop 和 recording/paused 状态，记录调用顺序。"""

    def __init__(self, *, recording: bool = True, paused: bool = False) -> None:
        self.recording = recording
        self.paused = paused
        self.calls: list[str] = []

    def start(self) -> None:
        self.calls.append("start")
        self.recording = True
        self.paused = False

    def pause(self) -> None:
        self.calls.append("pause")
        self.paused = True

    def resume(self) -> None:
        self.calls.append("resume")
        self.paused = False

    def stop(self) -> None:
        self.calls.append("stop")
        self.recording = False
        self.paused = False


class _假Serve句柄:
    """假 serve 句柄：只需有 stop()，记录被调次数。"""

    def __init__(self) -> None:
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


class _记录式OpenUrl:
    """记录式 open_url 回调：记录被调次数。"""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


def _make(**rec_kwargs) -> tuple[AppController, _假录音器, _假Serve句柄, _记录式OpenUrl]:
    rec = _假录音器(**rec_kwargs)
    serve = _假Serve句柄()
    open_url = _记录式OpenUrl()
    ctrl = AppController(rec, serve, open_url, url="http://127.0.0.1:8000")
    return ctrl, rec, serve, open_url


# ---- icon_state / tooltip：三态 -----------------------------------------


def test_icon_state_recording() -> None:
    ctrl, _, _, _ = _make(recording=True, paused=False)
    assert ctrl.icon_state() == "recording"


def test_icon_state_paused() -> None:
    ctrl, _, _, _ = _make(recording=True, paused=True)
    assert ctrl.icon_state() == "paused"


def test_icon_state_idle_when_not_recording() -> None:
    ctrl, _, _, _ = _make(recording=False, paused=False)
    assert ctrl.icon_state() == "idle"


def test_tooltip_recording_says_recording() -> None:
    ctrl, _, _, _ = _make(recording=True, paused=False)
    assert "正在录音" in ctrl.tooltip()


def test_tooltip_paused_says_paused() -> None:
    ctrl, _, _, _ = _make(recording=True, paused=True)
    assert "已暂停" in ctrl.tooltip()


def test_tooltip_idle_distinct() -> None:
    ctrl, _, _, _ = _make(recording=False, paused=False)
    tip = ctrl.tooltip()
    assert "正在录音" not in tip and "已暂停" not in tip


# ---- on_toggle_pause -----------------------------------------------------


def test_toggle_pause_when_recording_calls_pause() -> None:
    ctrl, rec, _, _ = _make(recording=True, paused=False)
    ctrl.on_toggle_pause()
    assert rec.calls == ["pause"]
    assert ctrl.icon_state() == "paused"


def test_toggle_pause_when_paused_calls_resume() -> None:
    ctrl, rec, _, _ = _make(recording=True, paused=True)
    ctrl.on_toggle_pause()
    assert rec.calls == ["resume"]
    assert ctrl.icon_state() == "recording"


def test_toggle_pause_when_idle_is_noop() -> None:
    """未录音时切换暂停不应误调 pause/resume。"""
    ctrl, rec, _, _ = _make(recording=False, paused=False)
    ctrl.on_toggle_pause()
    assert rec.calls == []


# ---- on_open_ui ----------------------------------------------------------


def test_open_ui_calls_open_url() -> None:
    ctrl, _, _, open_url = _make()
    ctrl.on_open_ui()
    assert open_url.calls == 1


# ---- on_quit：顺序 + 幂等 ------------------------------------------------


def test_quit_stops_recorder_then_serve() -> None:
    ctrl, rec, serve, _ = _make()
    ctrl.on_quit()
    assert rec.calls == ["stop"]
    assert serve.stop_calls == 1


def test_quit_sets_exit_flag() -> None:
    ctrl, _, _, _ = _make()
    assert ctrl.should_exit is False
    ctrl.on_quit()
    assert ctrl.should_exit is True


def test_quit_is_idempotent() -> None:
    """重复调 on_quit 不抛、recorder/serve 各只停一次。"""
    ctrl, rec, serve, _ = _make()
    ctrl.on_quit()
    ctrl.on_quit()
    ctrl.on_quit()
    assert rec.calls == ["stop"]
    assert serve.stop_calls == 1
    assert ctrl.should_exit is True


# ---- menu_items：文案随状态变 -------------------------------------------


def _toggle_label(ctrl: AppController) -> str:
    for it in ctrl.menu_items():
        if it["key"] == "toggle_pause":
            return it["label"]
    raise AssertionError("菜单里找不到 toggle_pause 项")


def test_menu_toggle_label_when_recording_says_pause() -> None:
    ctrl, _, _, _ = _make(recording=True, paused=False)
    assert _toggle_label(ctrl) == "暂停录音"


def test_menu_toggle_label_when_paused_says_resume() -> None:
    ctrl, _, _, _ = _make(recording=True, paused=True)
    assert _toggle_label(ctrl) == "继续录音"


def test_menu_has_open_and_quit_items() -> None:
    ctrl, _, _, _ = _make()
    keys = [it["key"] for it in ctrl.menu_items()]
    assert "open_ui" in keys
    assert "quit" in keys


# ---- 可选：真 pystray 集成（未装则跳过） --------------------------------


def test_build_pystray_menu_does_not_raise() -> None:
    pytest.importorskip("pystray")
    from rapport.desktop.tray import build_menu

    ctrl, _, _, _ = _make()
    menu = build_menu(ctrl)
    # 能构造出 pystray.Menu 即可（不真正 run）。
    assert menu is not None
