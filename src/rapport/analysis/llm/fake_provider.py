"""确定性假实现：给测试与演示用，绝不联网、绝不冒充真模型产出。

诚实是硬原则：FakeProvider 不做任何真实分析，它只是按 schema 造一个可预测的
占位结构——把提示里出现的话语 id 当引用，point 文案统一以「（示例）」前缀明示
这是占位、不是模型的真分析。这样前端能跑通「解读 + 原话出处」的完整链路，又
不会让用户误以为看到的是真洞察。
"""

from __future__ import annotations

import re
from typing import Any

# 匹配 user 提示里形如 "[12] 老王: ..." 的行首 utterance 编号。
_ID_RE = re.compile(r"\[(\d+)\]")


class FakeProvider:
    """按 schema 产出确定性占位结果的 provider。"""

    def generate_json(
        self, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """造一个符合 schema 的可预测 dict（不联网、不分析）。

        策略：
        - 从 user 提示里抠出最多前 2 个出现的 utterance_id 当引用依据；
        - overview 与 point 都加「（示例）」前缀，明示是占位文案；
        - 完全确定：相同输入永远得到相同输出，便于断言。
        """
        ids = self._first_ids(user, limit=2)
        # 取任务（system 第一行）拼进占位文案，让示例稍有上下文但仍明显是假的。
        task = (system or "").strip().splitlines()
        task_hint = task[0] if task else "解读"
        return {
            "overview": f"（示例）这是占位概览，未接入真模型；任务：{task_hint}。",
            "findings": [
                {
                    "point": (
                        "（示例）这是占位判断，非真模型产出；"
                        "设置 ANTHROPIC_API_KEY 并切到 anthropic 即可看真分析。"
                    ),
                    "quote_utterance_ids": ids,
                }
            ],
        }

    @staticmethod
    def _first_ids(user: str, limit: int) -> list[int]:
        """从提示文本里按出现顺序取最多 limit 个去重的 utterance_id。"""
        out: list[int] = []
        for m in _ID_RE.finditer(user or ""):
            v = int(m.group(1))
            if v not in out:
                out.append(v)
            if len(out) >= limit:
                break
        return out
