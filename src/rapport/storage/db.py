"""SQLite 存储层：建库、入库、按对话/人查询、FTS5 全文检索、改说话人归属。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from ..transcribe.base import Segment

# schema.sql 与本文件同目录，打包后随包分发。
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class Database:
    """Rapport 的 SQLite 存储门面。

    封装连接管理与建表，并提供对话/人/话语的增查与全文检索。
    默认使用内存库（:memory:），也可传入文件路径做持久化。
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        """打开（或新建）数据库并建好全部表。

        Args:
            path: 数据库文件路径；":memory:" 表示内存库。
        """
        self.path = path
        db_arg = path if path == ":memory:" else str(path)
        self._conn = sqlite3.connect(db_arg)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self) -> None:
        """执行 schema.sql 建表（幂等）。"""
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        self._conn.executescript(sql)
        self._conn.commit()

    # ---- 对话 ----------------------------------------------------------

    def add_conversation(
        self, audio_path: str | None = None, note: str | None = None
    ) -> int:
        """新建一次对话，返回自增 id。

        Args:
            audio_path: 关联音频文件路径，可空。
            note: 备注，可空。

        Returns:
            新对话的 id。
        """
        cur = self._conn.execute(
            "INSERT INTO conversation (audio_path, note) VALUES (?, ?)",
            (audio_path, note),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    # ---- 人 ------------------------------------------------------------

    def add_person(
        self,
        name: str,
        avatar: str | None = None,
        relation: str | None = None,
    ) -> int:
        """新建一个人，返回自增 id。

        Args:
            name: 姓名/昵称。
            avatar: 头像路径或标识，可空。
            relation: 关系描述，可空。

        Returns:
            新建人的 id。
        """
        cur = self._conn.execute(
            "INSERT INTO person (name, avatar, relation) VALUES (?, ?, ?)",
            (name, avatar, relation),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    # ---- 话语 ----------------------------------------------------------

    def add_utterance(
        self,
        conversation_id: int,
        text: str,
        speaker_label: str | None = None,
        person_id: int | None = None,
        start_ms: int = 0,
        end_ms: int = 0,
    ) -> int:
        """插入一句话语，返回自增 id。

        Args:
            conversation_id: 所属对话 id。
            text: 话语文本。
            speaker_label: 说话人标签（如 "A"/"B"），可空。
            person_id: 归属到的人 id，可空（未归属）。
            start_ms: 起始毫秒。
            end_ms: 结束毫秒。

        Returns:
            新话语的 id。
        """
        cur = self._conn.execute(
            "INSERT INTO utterance "
            "(conversation_id, person_id, speaker_label, text, start_ms, end_ms) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, person_id, speaker_label, text, start_ms, end_ms),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def add_segments(
        self, conversation_id: int, segments: list[Segment]
    ) -> list[int]:
        """批量写入转写片段，返回对应的话语 id 列表（与输入同序）。

        Args:
            conversation_id: 所属对话 id。
            segments: 转写片段列表。

        Returns:
            各片段对应的话语 id，顺序与 segments 一致。
        """
        ids: list[int] = []
        for seg in segments:
            cur = self._conn.execute(
                "INSERT INTO utterance "
                "(conversation_id, speaker_label, text, start_ms, end_ms) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    conversation_id,
                    seg.speaker_label,
                    seg.text,
                    seg.start_ms,
                    seg.end_ms,
                ),
            )
            ids.append(int(cur.lastrowid))
        self._conn.commit()
        return ids

    def get_utterances(self, conversation_id: int) -> list[sqlite3.Row]:
        """取某对话下全部话语，按 (start_ms, id) 升序。

        Args:
            conversation_id: 对话 id。

        Returns:
            话语行列表。
        """
        cur = self._conn.execute(
            "SELECT * FROM utterance WHERE conversation_id = ? "
            "ORDER BY start_ms, id",
            (conversation_id,),
        )
        return cur.fetchall()

    def get_utterances_for_person(self, person_id: int) -> list[sqlite3.Row]:
        """取归属到某个人的全部话语，按 (start_ms, id) 升序。

        Args:
            person_id: 人的 id。

        Returns:
            话语行列表。
        """
        cur = self._conn.execute(
            "SELECT * FROM utterance WHERE person_id = ? ORDER BY start_ms, id",
            (person_id,),
        )
        return cur.fetchall()

    def set_utterance_person(self, utterance_id: int, person_id: int | None) -> None:
        """修改某句话语的说话人归属。

        Args:
            utterance_id: 话语 id。
            person_id: 目标人 id；None 表示取消归属。
        """
        self._conn.execute(
            "UPDATE utterance SET person_id = ? WHERE id = ?",
            (person_id, utterance_id),
        )
        self._conn.commit()

    def search_utterances(self, query: str) -> list[sqlite3.Row]:
        """对话语文本做 FTS5 trigram 全文检索，按相关度（rank）排序。

        Args:
            query: 检索词（trigram 分词，中文需 ≥3 字以命中）。

        Returns:
            命中的话语行列表（含 utterance 全部字段）。
        """
        cur = self._conn.execute(
            "SELECT u.* FROM utterance_fts f "
            "JOIN utterance u ON u.id = f.rowid "
            "WHERE utterance_fts MATCH ? "
            "ORDER BY f.rank",
            (query,),
        )
        return cur.fetchall()

    # ---- 生命周期 ------------------------------------------------------

    def close(self) -> None:
        """关闭数据库连接。"""
        self._conn.close()
