"""按需分析包：可插拔 LLM 抽象 + 范围检索 + 带原话出处的解读。

对外暴露：
- get_provider()：按 config.LLM_PROVIDER 返回 provider 实例（none → None）；
- AnalysisError：解读失败的统一异常（web 层据此返回 status:error）。
具体的 summarize_conversation / analyze_person 等在 analysis.analyze 模块。
"""

from __future__ import annotations

from .llm.base import AnalysisError, LLMProvider

__all__ = ["AnalysisError", "LLMProvider", "get_provider"]


def get_provider() -> LLMProvider | None:
    """按 config.LLM_PROVIDER 返回对应 provider；"none"（未配置）返回 None。

    各实现的第三方依赖（anthropic / requests）都在各自模块里惰性 import，
    这里只做选择与构造，不会因为没装某个 SDK 而导入失败。

    Raises:
        AnalysisError: LLM_PROVIDER 取值不被支持时。
    """
    from .. import config

    name = (config.LLM_PROVIDER or "none").strip().lower()
    if name == "none":
        return None
    if name == "fake":
        from .llm.fake_provider import FakeProvider

        return FakeProvider()
    if name == "anthropic":
        from .llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    if name == "ollama":
        from .llm.ollama_provider import OllamaProvider

        return OllamaProvider()
    raise AnalysisError(f"不支持的 LLM_PROVIDER 取值：{name!r}")
