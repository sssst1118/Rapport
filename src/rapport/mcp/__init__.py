"""Rapport MCP 层：把本地只读数据做成结构化工具暴露给 AI 助手（Claude Desktop / Cursor）。

分层纪律：
- tools.py 纯逻辑、零 mcp 依赖，可纯单测。
- server.py 才 import mcp SDK，做薄传输层封装。
"""
