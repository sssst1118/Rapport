"""Anthropic 后端：用官方 anthropic Python SDK 调 Claude 做结构化分析。

要点（依据权威 claude-api 指引）：
- 模型默认 claude-opus-4-8（当前最强 Opus），可被 config.LLM_MODEL 覆盖。
- 用 messages.create + output_config.format 的 json_schema，保证首个 text block
  是合法 JSON，取出后 json.loads。
- thinking={"type":"adaptive"}（4.8 只支持 adaptive；budget_tokens 会 400）。
- 不传 temperature/top_p（4.8 会 400），不用 assistant prefill。
- anthropic 在方法内部惰性 import：未安装时整包仍可导入、测试不依赖它。
- 捕获 anthropic 异常 → 抛成本模块 AnalysisError，让 web 层返回 status:error。
"""

from __future__ import annotations

import json
from typing import Any

from .base import AnalysisError

# 默认模型：当前最强 Opus。别为省钱换小模型（产品诉求是解读质量）。
_DEFAULT_MODEL = "claude-opus-4-8"


class AnthropicProvider:
    """调用 Claude 的 LLMProvider 实现。"""

    def __init__(self, model: str | None = None) -> None:
        """记录模型名与 api key；不在这里建客户端（惰性，避免无 key/无包时构造即失败）。

        Args:
            model: 模型 id；缺省读 config.LLM_MODEL（再缺省 claude-opus-4-8）。

        api key 取自 config.anthropic_api_key()（裸 env ANTHROPIC_API_KEY >
        config.json anthropic_api_key > None）。为 None 时把 client 构造交给 SDK
        默认行为（仍会自动从 env 读，env 也没有则报缺 key），与改前等价。
        """
        self.api_key: str | None = None
        try:
            from ... import config

            if model is None:
                model = getattr(config, "LLM_MODEL", _DEFAULT_MODEL)
            self.api_key = config.anthropic_api_key()
        except Exception:  # noqa: BLE001 - 配置不可用也不该阻断构造
            if model is None:
                model = _DEFAULT_MODEL
        self.model = model or _DEFAULT_MODEL

    def generate_json(
        self, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """调用 Claude，返回符合 schema 的 dict。

        Raises:
            AnalysisError: SDK 未安装、调用失败或返回不可解析时（中文原因）。
        """
        # 惰性 import：未装 anthropic 时整包仍可导入、测试不触发。
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - 取决于运行环境是否装包
            raise AnalysisError(
                "未安装 anthropic SDK。请执行 pip install anthropic。"
            ) from exc

        try:
            # key 优先用 config 解析出的（env ANTHROPIC_API_KEY > config.json）；
            # 为 None 时退回 SDK 默认行为（自动从环境变量读）。
            client = (
                anthropic.Anthropic(api_key=self.api_key)
                if self.api_key
                else anthropic.Anthropic()
            )
            resp = client.messages.create(
                model=self.model,
                max_tokens=16000,
                thinking={"type": "adaptive"},
                output_config={
                    "format": {"type": "json_schema", "schema": schema}
                },
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.APIError as exc:  # SDK 层错误（401/400/429/5xx/网络等）
            raise AnalysisError(self._explain(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - 兜底，绝不把裸异常漏给 web 层
            raise AnalysisError(f"模型调用失败：{exc}") from exc

        # 安全分类器拒绝时是 HTTP 200 但 stop_reason=="refusal"，content 可能为空/不合 schema。
        # 先识别它，给出诚实的中文原因，避免误报成「未返回文本/不是合法 JSON」。
        if getattr(resp, "stop_reason", None) == "refusal":
            raise AnalysisError("语言模型基于安全策略拒绝了本次解读请求。")

        # output_config.format 保证首个 text block 是合法 JSON。
        try:
            text = next(b.text for b in resp.content if b.type == "text")
        except StopIteration as exc:
            raise AnalysisError("模型未返回文本内容。") from exc
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AnalysisError("模型返回的内容不是合法 JSON。") from exc
        if not isinstance(data, dict):
            raise AnalysisError("模型返回的 JSON 顶层不是对象。")
        return data

    @staticmethod
    def _explain(exc: Exception) -> str:
        """把 anthropic 异常翻成面向用户的中文原因（不泄露堆栈）。"""
        import anthropic

        if isinstance(exc, anthropic.AuthenticationError):
            return "语言模型鉴权失败：请检查 ANTHROPIC_API_KEY 是否正确。"
        if isinstance(exc, anthropic.RateLimitError):
            return "语言模型调用过于频繁（限流），请稍后重试。"
        if isinstance(exc, anthropic.APIConnectionError):
            return "无法连接到语言模型服务，请检查网络。"
        if isinstance(exc, anthropic.BadRequestError):
            return f"语言模型拒绝了请求：{getattr(exc, 'message', exc)}"
        return f"语言模型调用失败：{getattr(exc, 'message', exc)}"
