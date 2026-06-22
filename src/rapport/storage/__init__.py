"""存储层：基于 SQLite 的本地持久化（含 FTS5 全文检索）。"""

from __future__ import annotations

from .db import Database

__all__ = ["Database"]
