"""按需分析：把范围内话语喂给 provider，拿回带「原话出处」的解读。

每个公开函数对应一类解读（对话摘要 / 人物分析 / brief / 划选 / 复盘），统一：
1. 检索——按范围取话语（无需向量库，demo 量级、范围明确）；
2. 组装提示——把话语带 utterance_id 列进 user 提示，system 说明任务并要求每条
   判断引用它依据的 utterance_id；
3. 调 provider.generate_json 拿 {overview, findings:[{point, quote_utterance_ids}]}；
4. 把每个 utterance_id 解析成完整 Citation，丢弃指向不存在 id 的引用。

返回结构统一为 {overview, findings:[{point, quotes:[Citation...]}]}。
"""

from __future__ import annotations

from typing import Any

from .llm.base import AnalysisError

# 结构化输出 schema：要求 overview + findings，每条 finding 给出 point 与它依据的
# utterance_id 列表。含 required 与 additionalProperties:false（Claude 结构化输出要求）。
OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "point": {"type": "string"},
                    "quote_utterance_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                    },
                },
                "required": ["point", "quote_utterance_ids"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["overview", "findings"],
    "additionalProperties": False,
}


# ---- 提示组装 ------------------------------------------------------------


def _format_utterances(db: Any, rows: list[Any]) -> str:
    """把话语行渲染成带 id 编号的 user 提示文本。

    形如 `[12] 老王: 下个季度…`；未归属时用 speaker_label 兜底，再无则「未知」。
    顺带缓存 person 名字，避免逐行查库。
    """
    name_cache: dict[int, str | None] = {}

    def speaker_of(row: Any) -> str:
        pid = row["person_id"]
        if pid is not None:
            if pid not in name_cache:
                p = db.get_person(pid)
                name_cache[pid] = p["name"] if p else None
            if name_cache[pid]:
                return name_cache[pid]
        label = row["speaker_label"]
        return f"说话人{label}" if label else "未知"

    lines = [
        f"[{row['id']}] {speaker_of(row)}: {row['text']}" for row in rows
    ]
    return "\n".join(lines)


def _run(
    db: Any,
    provider: Any,
    system: str,
    rows: list[Any],
    allowed_ids: set[int] | None = None,
    lang: str = "zh",
) -> dict[str, Any]:
    """通用流水线：组装提示→调 provider→把引用解析成完整 Citation。

    范围内没有任何话语时，不调模型，直接返回空概览（诚实：没素材就没解读）。

    Args:
        allowed_ids: 若给定，引用只保留该集合内的 utterance_id（划选场景用，
            防止模型引到用户没选中的句子——挂的虽仍是真话，但越出了所选范围）。
        lang: 解读输出语言，跟随界面语言（"en" 让模型用英文产出，其余默认中文）。
    """
    if not rows:
        empty = (
            "No utterances to analyze in this scope."
            if lang == "en"
            else "范围内没有可供分析的话语。"
        )
        return {"overview": empty, "findings": []}

    # 让解读输出语言跟随界面（系统提示是中文，附一句英文指令即可切英文产出）。
    if lang == "en":
        system = system + "\n\nWrite the overview and every point in natural, concise English."

    user = (
        _format_utterances(db, rows)
        + "\n\n请针对上面的话语完成任务。每条判断都要在 quote_utterance_ids 里"
        "列出它依据的话语编号（方括号里的数字）。"
    )
    raw = provider.generate_json(system, user, OUTPUT_SCHEMA)
    if not isinstance(raw, dict):
        raise AnalysisError("模型返回结构异常。")

    findings_out: list[dict[str, Any]] = []
    for finding in raw.get("findings", []) or []:
        if not isinstance(finding, dict):
            continue
        quotes: list[dict[str, Any]] = []
        seen: set[int] = set()
        for raw_id in finding.get("quote_utterance_ids", []) or []:
            try:
                uid = int(raw_id)
            except (TypeError, ValueError):
                continue
            if uid in seen:
                continue  # 同一条判断重复引用同一句 → 去重（避免前端撞 key）
            if allowed_ids is not None and uid not in allowed_ids:
                continue  # 划选场景：只保留用户实际选中的句子
            seen.add(uid)
            c = _citation(db, uid)
            if c is not None:
                quotes.append(c)
        findings_out.append(
            {"point": finding.get("point", ""), "quotes": quotes}
        )
    return {"overview": raw.get("overview", ""), "findings": findings_out}


# ---- 引用解析：utterance_id → 完整 Citation -----------------------------


def _citation(db: Any, utterance_id: Any) -> dict[str, Any] | None:
    """把一个 utterance_id 解析成完整 Citation，指向不存在的 id 返回 None。

    Citation = {utterance_id, conversation_id, text, start_ms, end_ms,
    speaker_label, person_name}；person_name 由 person_id→db.get_person 得到，
    未归属为 None。
    """
    try:
        uid = int(utterance_id)
    except (TypeError, ValueError):
        return None
    row = _get_utterance(db, uid)
    if row is None:
        return None
    person_name: str | None = None
    if row["person_id"] is not None:
        p = db.get_person(row["person_id"])
        person_name = p["name"] if p else None
    return {
        "utterance_id": row["id"],
        "conversation_id": row["conversation_id"],
        "text": row["text"],
        "start_ms": row["start_ms"],
        "end_ms": row["end_ms"],
        "speaker_label": row["speaker_label"],
        "person_name": person_name,
    }


def _get_utterance(db: Any, utterance_id: int) -> Any | None:
    """按 id 取单条话语行（不存在返回 None）。

    db.py（冻结）没有单条取话语的公共方法，分两种来源取：
    - web 层的 _DbProxy 提供 get_utterance（在工作线程内执行查询，满足 SQLite
      连接线程封闭）——优先走它；
    - 测试里直接传进来的 Database 没有该方法，回退到对 _conn 执行只读 SQL。
    """
    getter = getattr(db, "get_utterance", None)
    if callable(getter):
        return getter(utterance_id)
    cur = db._conn.execute(
        "SELECT * FROM utterance WHERE id = ?", (utterance_id,)
    )
    return cur.fetchone()


# ---- 五类解读 ------------------------------------------------------------


def summarize_conversation(
    db: Any, provider: Any, conversation_id: int, lang: str = "zh"
) -> dict[str, Any]:
    """对话摘要：取该对话全部话语，给一段顶部概览与几条要点。"""
    rows = db.get_utterances(conversation_id)
    system = (
        "你是人际对话助手。请基于下面这段对话，给出简短的顶部摘要："
        "聊了什么、关键结论、需要跟进的事。每条判断引用它依据的话语编号。"
    )
    return _run(db, provider, system, list(rows), lang=lang)


def analyze_person(
    db: Any, provider: Any, person_id: int, lang: str = "zh"
) -> dict[str, Any]:
    """人物分析：取该人跨对话全部话语，分析沟通风格 / 在意什么 / 承诺待办。"""
    rows = db.get_utterances_for_person(person_id)
    system = (
        "你是人际对话助手。请基于这个人跨多次对话说过的话，分析他的沟通风格、"
        "在意什么、做过哪些承诺或待办、有哪些没了结的话头。"
        "每条判断引用它依据的话语编号。"
    )
    return _run(db, provider, system, list(rows), lang=lang)


def meeting_brief(
    db: Any, provider: Any, person_id: int, lang: str = "zh"
) -> dict[str, Any]:
    """见面前 brief：同样取该人跨对话话语，偏「下次见面前该记得什么」。"""
    rows = db.get_utterances_for_person(person_id)
    system = (
        "你是人际对话助手。马上要和这个人见面，请基于过往对话给一份见面前提要："
        "上次聊到哪、有哪些待办或承诺要跟进、有哪些话题适合接着聊、有哪些雷区。"
        "每条判断引用它依据的话语编号。"
    )
    return _run(db, provider, system, list(rows), lang=lang)


def analyze_selection(
    db: Any, provider: Any, utterance_ids: list[int], lang: str = "zh"
) -> dict[str, Any]:
    """划选分析：对给定的若干 utterance_id 做就事论事的解读。"""
    rows = [r for r in (_get_utterance(db, uid) for uid in utterance_ids) if r]
    allowed = {r["id"] for r in rows}
    system = (
        "你是人际对话助手。请就用户划选的这几句话做就事论事的解读："
        "对方可能的意思、言外之意、值得注意的地方。每条判断引用它依据的话语编号。"
    )
    # 收敛：划选场景下，引用只许落在用户实际选中的句子上。
    return _run(db, provider, system, rows, allowed_ids=allowed, lang=lang)


def review(
    db: Any, provider: Any, scope: str, id: int | None, lang: str = "zh"
) -> dict[str, Any]:
    """复盘：对话或人物范围，给『你的视角 / 对方视角 / 接下来怎么做』。

    Args:
        scope: "conversation" → 该对话全部话语；"person" → 该人跨对话话语。
        id: 对应的 conversation_id 或 person_id。
    """
    if scope == "conversation" and id is not None:
        rows = list(db.get_utterances(id))
    elif scope == "person" and id is not None:
        rows = list(db.get_utterances_for_person(id))
    else:
        rows = []
    system = (
        "你是人际对话助手。请基于这段记录做一次复盘，分别给出："
        "你（说话人「我」）当时可能的视角、对方可能的视角、接下来可以怎么做。"
        "每条判断引用它依据的话语编号。"
    )
    return _run(db, provider, system, rows, lang=lang)
