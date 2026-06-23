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

    def __init__(
        self,
        path: str | Path = ":memory:",
        check_same_thread: bool = True,
    ) -> None:
        """打开（或新建）数据库并建好全部表。

        Args:
            path: 数据库文件路径；":memory:" 表示内存库。
            check_same_thread: 传给 sqlite3.connect 的同名参数（默认 True）。
                MCP server 等在单一事件循环线程上使用时可传 False 作冗余保险。
        """
        self.path = path
        db_arg = path if path == ":memory:" else str(path)
        self._conn = sqlite3.connect(db_arg, check_same_thread=check_same_thread)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        if path != ":memory:":
            # 文件库启用 WAL：常驻守护进程与 rapport serve 可能同时读写同一个库，
            # WAL 让读写并发不互斥，避免 database is locked。:memory: 不支持 WAL，
            # 故仅对文件库启用（PRAGMA 返回实际生效模式，内存库会回落不在此分支）。
            self._conn.execute("PRAGMA journal_mode = WAL")
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

    # 常驻记录每日容器的 note 标记前缀；按它精确识别「当天」conversation，
    # 不与用户普通对话（即便 note 恰含日期数字）混淆。
    DAILY_NOTE_PREFIX = "常驻记录 · "

    def get_or_create_daily_conversation(
        self, day_str: str, audio_path: str
    ) -> int:
        """取或建某个自然日的「常驻记录」conversation，返回其 id。

        常驻 always-on 录音以「按自然日」分桶：每个本地日历日一个 conversation。
        同一天多次调用（含守护进程重启）都续写同一个；不同天各自独立。
        靠 note 精确标记 `常驻记录 · {day_str}` 识别，避免误命中普通对话。

        Args:
            day_str: 本地日期串（如 "2026-06-23"）。
            audio_path: 该天 day-WAV 的路径（新建时写入；已存在不覆盖）。

        Returns:
            当天 conversation 的 id。
        """
        note = f"{self.DAILY_NOTE_PREFIX}{day_str}"
        cur = self._conn.execute(
            "SELECT id FROM conversation WHERE note = ? ORDER BY id LIMIT 1",
            (note,),
        )
        row = cur.fetchone()
        if row is not None:
            return int(row["id"])
        return self.add_conversation(audio_path=audio_path, note=note)

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

    # ---- M3：以人为中心的查询 ------------------------------------------

    def list_persons(self) -> list[sqlite3.Row]:
        """列出全部人物，按更新时间倒序、id 倒序（最近活跃在前）。

        Returns:
            人物行列表。
        """
        cur = self._conn.execute(
            "SELECT * FROM person ORDER BY updated_at DESC, id DESC"
        )
        return cur.fetchall()

    def get_person(self, person_id: int) -> sqlite3.Row | None:
        """按 id 取单个人物，不存在返回 None。

        Args:
            person_id: 人的 id。

        Returns:
            人物行，或 None。
        """
        cur = self._conn.execute(
            "SELECT * FROM person WHERE id = ?", (person_id,)
        )
        return cur.fetchone()

    def get_conversation(self, conversation_id: int) -> sqlite3.Row | None:
        """按 id 取单个对话（含 audio_path、started_at、note），不存在返回 None。

        Args:
            conversation_id: 对话 id。

        Returns:
            对话行，或 None。
        """
        cur = self._conn.execute(
            "SELECT * FROM conversation WHERE id = ?", (conversation_id,)
        )
        return cur.fetchone()

    def list_conversations(self) -> list[sqlite3.Row]:
        """列出全部对话，按开始时间倒序、id 倒序（最近优先）。

        Returns:
            对话行列表。
        """
        cur = self._conn.execute(
            "SELECT * FROM conversation ORDER BY started_at DESC, id DESC"
        )
        return cur.fetchall()

    def get_persons_in_conversation(self, conversation_id: int) -> list[sqlite3.Row]:
        """取某对话里「在场的人」——有归属话语的去重人物，按首次开口先后排序。

        Args:
            conversation_id: 对话 id。

        Returns:
            人物行列表（无归属的话语不计入）。
        """
        cur = self._conn.execute(
            "SELECT p.* FROM person p "
            "JOIN utterance u ON u.person_id = p.id "
            "WHERE u.conversation_id = ? "
            "GROUP BY p.id "
            "ORDER BY MIN(u.start_ms), p.id",
            (conversation_id,),
        )
        return cur.fetchall()

    # ---- 标注 ----------------------------------------------------------

    def add_annotation(
        self,
        utterance_id: int,
        type: str,
        value: str | None = None,
        person_id: int | None = None,
    ) -> int:
        """给某句话语加一条标注（type 取 'speaker' | 'tag' | 'note'），返回自增 id。

        Args:
            utterance_id: 被标注的话语 id。
            type: 标注类型——说话人归属 / 标签 / 批注。
            value: 标签内容或批注文字，可空。
            person_id: 关联到的人 id（speaker 类型用），可空。

        Returns:
            新标注的 id。
        """
        cur = self._conn.execute(
            "INSERT INTO annotation (utterance_id, person_id, type, value) "
            "VALUES (?, ?, ?, ?)",
            (utterance_id, person_id, type, value),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def get_annotations(self, utterance_id: int) -> list[sqlite3.Row]:
        """取某句话语的全部标注，按创建时间、id 升序。

        Args:
            utterance_id: 话语 id。

        Returns:
            标注行列表。
        """
        cur = self._conn.execute(
            "SELECT * FROM annotation WHERE utterance_id = ? "
            "ORDER BY created_at, id",
            (utterance_id,),
        )
        return cur.fetchall()

    # ---- 话语编辑与说话人映射 ------------------------------------------

    def update_utterance_text(self, utterance_id: int, text: str) -> None:
        """编辑某句话语的转写文字（FTS 索引由触发器自动同步）。

        Args:
            utterance_id: 话语 id。
            text: 新文字。
        """
        self._conn.execute(
            "UPDATE utterance SET text = ? WHERE id = ?",
            (text, utterance_id),
        )
        self._conn.commit()

    def relabel_speaker(
        self, conversation_id: int, speaker_label: str, person_id: int | None
    ) -> int:
        """把某对话里某个说话人标签（如 "A"）的全部话语一次性归到某人名下。

        对应 §9.1「把这段里所有『说话人1』都变成老王」的快速映射，
        只影响给定对话内的该标签，不跨对话。

        Args:
            conversation_id: 对话 id。
            speaker_label: diarization 原始标签，如 "A"/"B"。
            person_id: 目标人 id；None 表示取消归属。

        Returns:
            受影响的话语条数。
        """
        cur = self._conn.execute(
            "UPDATE utterance SET person_id = ? "
            "WHERE conversation_id = ? AND speaker_label = ?",
            (person_id, conversation_id, speaker_label),
        )
        self._conn.commit()
        return cur.rowcount

    # ---- 生命周期 ------------------------------------------------------

    def close(self) -> None:
        """关闭数据库连接。"""
        self._conn.close()
