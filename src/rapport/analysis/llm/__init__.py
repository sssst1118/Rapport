"""可插拔 LLM 抽象层：base 协议 + fake/anthropic/ollama 三个实现。

对外只需 LLMProvider（接口）与 AnalysisError（异常）；具体实现按需在
analysis 包的 get_provider() 里惰性挑选，避免在此 import 第三方 SDK。
"""

from __future__ import annotations

from .base import AnalysisError, LLMProvider

__all__ = ["AnalysisError", "LLMProvider"]
