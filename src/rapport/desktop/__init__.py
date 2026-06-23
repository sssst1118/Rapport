"""桌面常驻形态：托盘 + serve + 常驻录音 Engine 的单进程编排。

分层（保证核心可纯单测、不依赖显示器/声卡/网络）：
- controller.AppController：纯逻辑。持有 recorder / serve 句柄 / open_url 回调，
  暴露菜单动作与图标状态。**顶部不导入 pystray / uvicorn / sounddevice。**
- tray：薄集成层，延迟导入 pystray + Pillow，把 controller 画成真实托盘图标。
- runtime：编排层，构造真实 Engine + 后台线程起 uvicorn serve + 浏览器回调，
  组装 AppController 交给 tray 运行。`rapport app` 子命令的落点。
"""
