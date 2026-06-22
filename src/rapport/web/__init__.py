"""Rapport Web 后端（FastAPI）。

对外暴露 create_app（应用工厂）。uvicorn 在 reload 模式下用 import string
`rapport.web:create_app`（--factory）拿到工厂，非 reload 模式由 serve 子命令直接
调用 create_app() 传入实例。本模块只在真正构建 app 时才连库，保持惰性。
"""

from __future__ import annotations

from .app import create_app

__all__ = ["create_app"]
