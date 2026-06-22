"""LLM 抽象层：定义 provider 接口与本模块统一异常。

设计目标——「换实现只改配置」：
- 所有具体实现（fake / anthropic / ollama）都实现同一个 LLMProvider 协议，
  核心方法是 generate_json(system, user, schema) → 返回符合该 JSON Schema 的 dict。
- 上层（analyze.py、web 端点）只依赖这个抽象，不感知具体后端。
- 任何后端的失败都向上抛成 AnalysisError，web 层据此返回 status:error（绝不 500）。

不在这里 import 任何具体 SDK（anthropic 等），保证未装第三方库时整包仍可导入、
测试也不依赖它。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class AnalysisError(Exception):
    """按需分析过程中的可向用户呈现的失败。

    凡是 provider 调用失败、网络不可达、返回不可解析等，都包成本异常向上抛；
    web 层捕获后返回 {"status": "error", "message": <中文原因>}，HTTP 仍 200。
    message 应是面向用户的中文说明，不泄露堆栈细节。
    """


@runtime_checkable
class LLMProvider(Protocol):
    """可插拔语言模型后端的统一接口。

    只需实现一个方法。用 Protocol 而非 ABC，便于「鸭子类型」注入（测试里随手
    写个带 generate_json 的类即可当 provider），同时保留静态类型检查能力。
    """

    def generate_json(
        self, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """按给定 JSON Schema 产出结构化结果。

        Args:
            system: 系统提示（描述任务与约束）。
            user: 用户提示（带 utterance_id 编号的范围内话语等）。
            schema: 期望输出遵循的 JSON Schema（含 required 与
                additionalProperties:false）。

        Returns:
            一个符合 schema 的 dict。

        Raises:
            AnalysisError: 后端调用失败或返回不可解析时。
        """
        ...
