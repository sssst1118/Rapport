"""Ollama 后端：本地模型，数据不出设备——最贴 Rapport「本地优先」的调性。

走 Ollama 的 HTTP /api/chat，并用**结构化输出**：把 JSON Schema 直接当 `format`
传给 Ollama（0.5+ 支持），由它在解码层约束模型只产出合规 JSON——比老式
`format: "json"` + 提示里塞 schema 可靠得多，7B 小模型也能稳定吐出合规结构。

只用标准库 urllib（零第三方依赖，更贴本地优先），并**显式禁用代理**直连本机
（本机若设了 http_proxy，默认会把 localhost 也代理掉导致连不上）。
模型/地址走 config.OLLAMA_MODEL / OLLAMA_HOST（默认本机 qwen2.5:7b、11434）。
连不上 / 解析失败一律抛 AnalysisError，由 web 层化为 status:error（绝不 500）。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .base import AnalysisError

_DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"
_DEFAULT_HOST = "http://localhost:11434"

# Ollama 永远在本机，显式禁用一切代理（绕过 http_proxy）直连。
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class OllamaProvider:
    """调用本地 Ollama 的 LLMProvider 实现（结构化输出，零第三方依赖）。"""

    def __init__(self, model: str | None = None, host: str | None = None) -> None:
        """模型/地址缺省读 config.OLLAMA_MODEL / OLLAMA_HOST。"""
        if model is None or host is None:
            try:
                from ... import config

                if model is None:
                    model = getattr(config, "OLLAMA_MODEL", _DEFAULT_MODEL)
                if host is None:
                    host = getattr(config, "OLLAMA_HOST", _DEFAULT_HOST)
            except Exception:  # noqa: BLE001 - 配置不可用也不该阻断构造
                pass
        self.model = model or _DEFAULT_MODEL
        self.host = (host or _DEFAULT_HOST).rstrip("/")

    def generate_json(
        self, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """调用 Ollama /api/chat，用 schema 约束输出，返回 dict。

        Raises:
            AnalysisError: 连不上、模型不存在或返回不可解析时（中文原因）。
        """
        payload = json.dumps(
            {
                "model": self.model,
                # 结构化输出：直接把 JSON Schema 当 format 传，Ollama 在解码层
                # 约束模型只产出合规 JSON（0.5+ 支持）。
                "format": schema,
                "stream": False,
                "options": {"temperature": 0},  # 稳定、可复现
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            # 本地 7B 首字可能较慢（含模型加载），给足超时。
            with _OPENER.open(req, timeout=300) as resp:
                body = resp.read().decode("utf-8")
        except (urllib.error.URLError, OSError) as exc:  # 含连接/超时/HTTP/模型不存在
            raise AnalysisError(
                f"调用本地 Ollama 失败（{self.host}，模型 {self.model}）：{exc}。"
                "请确认 Ollama 已运行、且已 `ollama pull` 该模型。"
            ) from exc

        try:
            content = json.loads(body)["message"]["content"]
            data = json.loads(content)
        except (KeyError, ValueError, TypeError) as exc:
            raise AnalysisError("Ollama 返回的内容不是合法 JSON。") from exc
        if not isinstance(data, dict):
            raise AnalysisError("Ollama 返回的 JSON 顶层不是对象。")
        return data
