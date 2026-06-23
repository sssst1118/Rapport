# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：把 `rapport app`（托盘常驻桌面应用）打成 Windows onedir 产物。

onedir（one-folder）而非 one-file：对 ctranslate2 / onnxruntime 等原生 dll 远更可靠、
启动也快；最终用 NSIS 把整个 dist/Rapport/ 文件夹包成单个 setup.exe 交付用户。

构建：
    .venv\\Scripts\\pyinstaller packaging\\rapport.spec
产物：
    dist/Rapport/Rapport.exe（双击即等价于 rapport app）

资源与冻结路径解析的对齐（见 src/rapport/_frozen.py）：
- frontend/dist  → bundle 内 `frontend/dist/`（web/app.py 冻结态从 sys._MEIPASS 取）
- schema.sql     → bundle 内 `rapport/storage/schema.sql`（storage/db.py 冻结态从资源根取）
- 可写数据（DB/day-WAV/状态文件）不随包，运行时落 %LOCALAPPDATA%\\Rapport。

不打包 whisper 模型（体积/协议/需联网）：首次转写时 faster-whisper 自行下载到 HF 缓存。
"""

from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
)

# spec 所在 = <repo>/packaging/，仓库根上溯一级。
REPO_ROOT = Path(SPECPATH).resolve().parent

datas = []
binaries = []
hiddenimports = []


def _merge(pkg, *, with_dynlibs=False):
    """collect_all 一个包并并入三大列表；可选额外 collect_dynamic_libs（原生 dll）。"""
    d, b, h = collect_all(pkg)
    datas.extend(d)
    binaries.extend(b)
    hiddenimports.extend(h)
    if with_dynlibs:
        binaries.extend(collect_dynamic_libs(pkg))


# ---- 重依赖：原生库与数据文件齐打 ----------------------------------------
# faster-whisper 转写链：ctranslate2（原生推理）+ tokenizers + huggingface_hub（下载）。
_merge("faster_whisper")
_merge("ctranslate2", with_dynlibs=True)
_merge("tokenizers")
_merge("huggingface_hub")
# VAD / 解码可能拉到的原生栈：onnxruntime（VAD）、av（PyAV，带 ffmpeg dll）。
_merge("onnxruntime", with_dynlibs=True)
_merge("av")
# 录音：sounddevice 带 PortAudio dll（_sounddevice_data 里）。
_merge("sounddevice")
datas += collect_data_files("_sounddevice_data")
binaries += collect_dynamic_libs("_sounddevice_data")
# 托盘：pystray（Windows 后端 win32）+ Pillow。
_merge("pystray")
_merge("PIL")

# ---- 随包只读资源（与 _frozen.resource_root() 的约定路径对齐） ------------
# 前端 SPA 构建产物 → bundle 内 frontend/dist/
datas.append((str(REPO_ROOT / "frontend" / "dist"), "frontend/dist"))
# 存储层 schema.sql → bundle 内 rapport/storage/schema.sql
datas.append(
    (str(REPO_ROOT / "src" / "rapport" / "storage" / "schema.sql"), "rapport/storage")
)

# ---- 常见漏项：动态/字符串导入 PyInstaller 静态分析抓不到 ------------------
hiddenimports += [
    # uvicorn 的 loop/protocol/lifespan 实现按字符串运行时选取。
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "uvicorn.logging",
    # pystray Windows 后端（win32）。
    "pystray._win32",
    # Rapport 各子模块（入口只显式 import desktop.runtime，确保整链都在）。
    "rapport.web",
    "rapport.web.app",
    "rapport.storage.db",
    "rapport.alwayson.engine",
    "rapport.alwayson.mic",
    "rapport.diarize",
    "rapport.diarize.single_speaker",
    "rapport.transcribe.local_whisper",
    "rapport.config",
    "rapport._frozen",
]

# ---- 体积裁剪：明确不需要进桌面应用的重包，排除以缩小产物 -----------------
excludes = [
    "gradio",        # CLI 的 `rapport ui` 才用，桌面 app 不需要。
    "gradio_client",
    "matplotlib",
    "tkinter",
    "pandas",
    "scipy",
]


a = Analysis(
    [str(REPO_ROOT / "packaging" / "launch.py")],
    pathex=[str(REPO_ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Rapport",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,        # windowed：托盘应用不弹黑窗。
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(REPO_ROOT / "packaging" / "rapport.ico")
    if (REPO_ROOT / "packaging" / "rapport.ico").is_file()
    else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Rapport",
)
