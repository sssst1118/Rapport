"""Rapport MCP server：用官方 mcp SDK 的高层 FastMCP，把 tools.py 的纯函数注册成 MCP 工具。

这是【唯一】import mcp 的文件——传输层薄封装，核心逻辑全在 tools.py（零 SDK 依赖、可纯单测）。

安全基线：只注册 7 个【只读】工具，绝不暴露任何写操作、绝不开放 raw SQL。stdio 传输是
本地进程管道、无网络，所以 stdio 模式不需要 API key（API key 是将来加 HTTP/SSE 传输时才需要）。

DB 生命周期：进程启动时按配置建一个 Database，所有工具共用。FastMCP 工具处理器是 async、
跑在事件循环单线程上，SQLite 连接需与使用它的线程一致——这里全程同一事件循环线程，故安全；
建连接时传 check_same_thread=False 作冗余保险（全为只读查询，安全）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..storage.db import Database
from . import tools


def _open_db(db_path: str | Path) -> Database:
    """按路径开一个只读使用的 Database（check_same_thread=False 作冗余保险）。

    所有工具跑在事件循环单线程，本来就同线程；check_same_thread=False 仅保险起见。
    """
    return Database(db_path, check_same_thread=False)


def build_server(db_path: str | Path | None = None) -> FastMCP:
    """构建并返回一个注册好全部 7 个只读工具的 FastMCP 实例。

    Args:
        db_path: 数据库路径；缺省读 config.DB_PATH（与 web 层一致，默认走
            RAPPORT_DB_PATH 环境变量）。传 ":memory:" 便于冒烟测试。

    Returns:
        配置好工具的 FastMCP 实例（未启动）。
    """
    if db_path is None:
        from .. import config

        db_path = config.DB_PATH

    db = _open_db(db_path)
    mcp = FastMCP("rapport")

    @mcp.tool()
    def list_people() -> list[dict[str, Any]]:
        """列出所有人物（含话语数、对话数）。"""
        return tools.list_people(db)

    @mcp.tool()
    def search_people(query: str) -> list[dict[str, Any]]:
        """按名字模糊查人（大小写不敏感子串匹配）。"""
        return tools.search_people(db, query)

    @mcp.tool()
    def get_person(person_id: int) -> dict[str, Any]:
        """取某人详情及其全部话语（带可回放出处 utterance_id/conversation_id/start_ms）。"""
        return tools.get_person(db, person_id)

    @mcp.tool()
    def get_conversation(conversation_id: int) -> dict[str, Any]:
        """取某次对话的完整纯数据（参与者+逐句话语+标注），供消费端 AI 自行复盘。"""
        return tools.get_conversation(db, conversation_id)

    @mcp.tool()
    def list_conversations() -> list[dict[str, Any]]:
        """列出全部对话（最近优先，含话语数与参与者）。"""
        return tools.list_conversations(db)

    @mcp.tool()
    def relationship_graph() -> dict[str, Any]:
        """关系网络：节点=人物，连线=同段对话共同在场推断的认识关系（含权重）。"""
        return tools.relationship_graph(db)

    @mcp.tool()
    def search_utterances(query: str) -> list[dict[str, Any]]:
        """全文检索话语并带出处（中文 query 需 ≥3 字；过短返回空）。"""
        return tools.search_utterances(db, query)

    return mcp


def run() -> None:
    """以 stdio 传输启动 MCP server（供 `rapport mcp` 子命令调用）。"""
    mcp = build_server()
    mcp.run(transport="stdio")
