"""托盘集成层：把 AppController 画成真实的 pystray 系统托盘图标。

pystray / PIL **延迟导入**（函数内 import），所以单测 controller 时不触发 GUI 依赖；
未装 pystray 时本模块仍可被导入（只有真正调用时才会失败）。

图标 = Pillow 运行时画的彩色圆点（无需打包图标文件）：
- recording → 红点；paused → 黄点；idle → 灰点。tooltip 跟随 controller.tooltip()。
icon.run() 占主线程（Windows 上最稳）。状态变化由调用方（runtime 的状态轮询线程或
菜单回调后）调 refresh() 把新图标/tooltip/菜单推给 pystray。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .controller import AppController

# 三态圆点颜色（RGB）。红=醒目录制指示，黄=暂停，灰=未录音。
_STATE_COLORS = {
    "recording": (220, 38, 38),   # 红
    "paused": (234, 179, 8),      # 黄
    "idle": (120, 120, 120),      # 灰
}


def _make_dot_image(color: tuple[int, int, int], size: int = 64) -> Any:
    """用 Pillow 画一个实心圆点图标（透明背景），运行时生成、无需图标文件。"""
    from PIL import Image, ImageDraw  # 延迟导入

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size // 8
    draw.ellipse((pad, pad, size - pad, size - pad), fill=(*color, 255))
    return img


def _image_for_state(state: str) -> Any:
    """按图标三态取对应颜色的圆点图标。未知态退回灰点。"""
    color = _STATE_COLORS.get(state, _STATE_COLORS["idle"])
    return _make_dot_image(color)


def build_menu(controller: AppController) -> Any:
    """据 controller.menu_items() 构造真实 pystray.Menu。

    toggle 项的 text 用 callable，pystray 每次显示菜单时回调取最新文案，
    配合 icon.update_menu() 即可让「暂停录音 ↔ 继续录音」随状态实时切换。
    """
    from pystray import Menu, MenuItem  # 延迟导入

    # 动作键 → controller 方法。
    actions = {
        "toggle_pause": controller.on_toggle_pause,
        "open_ui": controller.on_open_ui,
        "quit": controller.on_quit,
    }
    # label 用 callable，保证菜单展开时取当前文案（toggle 项随状态变）。
    label_callables = {
        "toggle_pause": lambda _i: controller._toggle_label(),
        "open_ui": lambda _i: "打开界面",
        "quit": lambda _i: "退出",
    }

    items = []
    for desc in controller.menu_items():
        key = desc["key"]
        action = actions[key]
        items.append(MenuItem(label_callables[key], _wrap_action(action)))
    return Menu(*items)


def _wrap_action(action):  # noqa: ANN001, ANN201
    """把 controller 的无参方法包成 pystray 期望的 (icon, item) 回调。"""

    def _handler(icon, item):  # noqa: ANN001
        action()

    return _handler


def build_icon(controller: AppController) -> Any:
    """据 controller 当前状态构造 pystray.Icon（图标 + tooltip + 菜单）。"""
    from pystray import Icon  # 延迟导入

    state = controller.icon_state()
    return Icon(
        "rapport",
        icon=_image_for_state(state),
        title=controller.tooltip(),
        menu=build_menu(controller),
    )


def refresh(icon: Any, controller: AppController) -> None:
    """把 controller 当前状态推给已运行的 pystray.Icon（图标 + tooltip + 菜单文案）。

    供状态轮询线程在录音态变化（如菜单暂停/恢复、Engine 自身停止）后调用，
    让红/黄/灰圆点与 tooltip 实时跟手。
    """
    state = controller.icon_state()
    icon.icon = _image_for_state(state)
    icon.title = controller.tooltip()
    try:
        icon.update_menu()
    except Exception:  # noqa: BLE001 - 某些后端无动态菜单，忽略
        pass
