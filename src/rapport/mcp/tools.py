"""MCP 工具的纯数据逻辑层——零 mcp 依赖，可纯单测。

每个工具 = 一个普通函数 `(db: Database, **params) -> 可 JSON 序列化的 dict/list`。
底层只调用 Database 的【只读】方法，绝不写库、绝不触发任何 LLM/analysis。

出处（citation）原则：凡返回话语，必带 utterance_id + conversation_id + start_ms/end_ms，
这是 Rapport「可回放原话出处」的硬要求，消费端据此跳播。

【重要】本文件顶部绝不 import mcp。只 import Database 与标准库。
"""

from __future__ import annotations

import sqlite3
from itertools import combinations
from typing import Any, Protocol, runtime_checkable

from ..storage.db import Database


@runtime_checkable
class GraphDataSource(Protocol):
    """build_graph（及其内部 _person_counts）所需的最小只读接口。

    Database 与 _DbProxy 都天然满足此协议（鸭子类型），无需显式继承。
    引入 Protocol 的目的：让 web 层调 build_graph(db) 时不需要 type: ignore。
    """

    def list_persons(self) -> list[sqlite3.Row]: ...

    def list_conversations(self) -> list[sqlite3.Row]: ...

    def get_persons_in_conversation(
        self, conversation_id: int
    ) -> list[sqlite3.Row]: ...

    def get_utterances_for_person(
        self, person_id: int
    ) -> list[sqlite3.Row]: ...


# ---- 共享小工具 ----------------------------------------------------------


def _person_counts(db: GraphDataSource, person_id: int) -> tuple[int, int]:
    """某人的 (话语数, 涉及对话数)，由现有只读方法推导。"""
    utts = db.get_utterances_for_person(person_id)
    conv_ids = {u["conversation_id"] for u in utts}
    return len(utts), len(conv_ids)


def _person_card(db: Database, row: sqlite3.Row) -> dict[str, Any]:
    """人物列表项：基本字段 + 话语数/对话数。"""
    utt_count, conv_count = _person_counts(db, row["id"])
    return {
        "id": row["id"],
        "name": row["name"],
        "relation": row["relation"],
        "avatar": row["avatar"],
        "utterance_count": utt_count,
        "conversation_count": conv_count,
    }


def _utterance_citation(row: sqlite3.Row) -> dict[str, Any]:
    """话语的「带出处」表示（用于 get_person / search_utterances）。"""
    return {
        "utterance_id": row["id"],
        "conversation_id": row["conversation_id"],
        "person_id": row["person_id"],
        "speaker_label": row["speaker_label"],
        "text": row["text"],
        "start_ms": row["start_ms"],
        "end_ms": row["end_ms"],
    }


def _participant(row: sqlite3.Row) -> dict[str, Any]:
    """对话参与者的精简表示。"""
    return {"id": row["id"], "name": row["name"], "relation": row["relation"]}


# ---- 关系图：可被 web 与 mcp 共享的纯构图函数 ----------------------------


def build_graph(db: GraphDataSource) -> dict[str, Any]:
    """关系网络：节点=人物（带话语数/对话数），连线=同段对话共同在场 → 推断彼此认识。

    连线权重 = 两人共同在场的对话数。这是从真实记录里「白捡」的关系，属事实层，
    不是模型脑补。web 层 /api/graph 与 mcp relationship_graph 共用本函数，避免两处重复。

    参数类型用 GraphDataSource Protocol 而非具体 Database，使 web 层传入
    _DbProxy 时无需 type: ignore（两者都满足该协议的鸭子类型约束）。
    """
    nodes = []
    for p in db.list_persons():
        utt_count, conv_count = _person_counts(db, p["id"])
        nodes.append(
            {
                "id": p["id"],
                "name": p["name"],
                "relation": p["relation"],
                "utterance_count": utt_count,
                "conversation_count": conv_count,
            }
        )
    pair_weight: dict[tuple[int, int], int] = {}
    for c in db.list_conversations():
        ids = sorted({p["id"] for p in db.get_persons_in_conversation(c["id"])})
        for a, b in combinations(ids, 2):
            pair_weight[(a, b)] = pair_weight.get((a, b), 0) + 1
    edges = [
        {"source": a, "target": b, "weight": w}
        for (a, b), w in pair_weight.items()
    ]
    return {"nodes": nodes, "edges": edges}


# ---- 7 个工具函数 --------------------------------------------------------


def list_people(db: Database) -> list[dict[str, Any]]:
    """所有人物列表（带话语数/对话数）。"""
    return [_person_card(db, p) for p in db.list_persons()]


def search_people(db: Database, query: str) -> list[dict[str, Any]]:
    """按名字大小写不敏感子串匹配查人（人名在内存侧过滤，FTS 留给话语）。"""
    needle = query.casefold()
    return [
        _person_card(db, p)
        for p in db.list_persons()
        if needle in (p["name"] or "").casefold()
    ]


def get_person(db: Database, person_id: int) -> dict[str, Any]:
    """单人详情 + ta 的话语（带可回放出处）。不存在 → error dict，不抛异常。"""
    p = db.get_person(person_id)
    if p is None:
        return {"error": "person not found", "person_id": person_id}
    utterances = [
        {
            "utterance_id": u["id"],
            "conversation_id": u["conversation_id"],
            "speaker_label": u["speaker_label"],
            "text": u["text"],
            "start_ms": u["start_ms"],
            "end_ms": u["end_ms"],
        }
        for u in db.get_utterances_for_person(person_id)
    ]
    return {
        "person": {
            "id": p["id"],
            "name": p["name"],
            "relation": p["relation"],
            "avatar": p["avatar"],
        },
        "utterances": utterances,
    }


def get_conversation(db: Database, conversation_id: int) -> dict[str, Any]:
    """对话详情（meeting-recap 的纯数据版）：参与者 + 逐句话语 + 标注。

    让消费端 AI 自己复盘。不存在 → error dict。
    """
    c = db.get_conversation(conversation_id)
    if c is None:
        return {"error": "conversation not found", "conversation_id": conversation_id}
    utterances = []
    for u in db.get_utterances(conversation_id):
        anns = [
            {"id": a["id"], "type": a["type"], "value": a["value"]}
            for a in db.get_annotations(u["id"])
        ]
        utterances.append(
            {
                "utterance_id": u["id"],
                "person_id": u["person_id"],
                "speaker_label": u["speaker_label"],
                "text": u["text"],
                "start_ms": u["start_ms"],
                "end_ms": u["end_ms"],
                "annotations": anns,
            }
        )
    participants = [
        _participant(p) for p in db.get_persons_in_conversation(conversation_id)
    ]
    return {
        "conversation": {
            "id": c["id"],
            "started_at": c["started_at"],
            "note": c["note"],
        },
        "participants": participants,
        "utterances": utterances,
    }


def list_conversations(db: Database) -> list[dict[str, Any]]:
    """对话列表（最近优先，带话语数与参与者）。"""
    out = []
    for c in db.list_conversations():
        utterances = db.get_utterances(c["id"])
        participants = [
            _participant(p) for p in db.get_persons_in_conversation(c["id"])
        ]
        out.append(
            {
                "id": c["id"],
                "started_at": c["started_at"],
                "note": c["note"],
                "utterance_count": len(utterances),
                "participants": participants,
            }
        )
    return out


def relationship_graph(db: Database) -> dict[str, Any]:
    """关系网络（ego「我」+ 共现连线）。复用 build_graph 的构图逻辑。"""
    return build_graph(db)


def search_utterances(db: Database, query: str) -> list[dict[str, Any]]:
    """全文检索话语，带出处。query 太短（中文 <3 字）FTS 可能报错——捕获返回 []。"""
    try:
        rows = db.search_utterances(query)
    except sqlite3.OperationalError:
        return []
    return [_utterance_citation(r) for r in rows]
