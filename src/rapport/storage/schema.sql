-- Rapport 存储层 schema（SQLite）。
-- 6 张业务表 + utterance.text 的 FTS5 全文检索（外部内容表 + trigram 分词）。
-- 全部 IF NOT EXISTS，可重复执行（幂等）。

-- 人：联系人/说话人主体。
CREATE TABLE IF NOT EXISTS person (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    avatar     TEXT,
    relation   TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 对话：一次录音/转写会话。
CREATE TABLE IF NOT EXISTS conversation (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    audio_path TEXT,
    note       TEXT
);

-- 话语：一句转写文本，可归属到某个人。
CREATE TABLE IF NOT EXISTS utterance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversation(id) ON DELETE CASCADE,
    person_id       INTEGER REFERENCES person(id) ON DELETE SET NULL,
    speaker_label   TEXT,
    text            TEXT NOT NULL,
    start_ms        INTEGER NOT NULL DEFAULT 0,
    end_ms          INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_utterance_conversation
    ON utterance(conversation_id, start_ms, id);
CREATE INDEX IF NOT EXISTS idx_utterance_person
    ON utterance(person_id, start_ms, id);

-- 标注：对某句话语的人工/自动标注。
CREATE TABLE IF NOT EXISTS annotation (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    utterance_id INTEGER NOT NULL REFERENCES utterance(id) ON DELETE CASCADE,
    person_id    INTEGER REFERENCES person(id) ON DELETE SET NULL,
    type         TEXT NOT NULL,
    value        TEXT,
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 画像：某个人的累积画像文本。
CREATE TABLE IF NOT EXISTS profile (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id  INTEGER NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    content    TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 关系：某个人与「我」之间的关系刻画。
CREATE TABLE IF NOT EXISTS relationship (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    kind      TEXT,
    strength  REAL,
    note      TEXT
);

-- FTS5 全文检索：外部内容表指向 utterance，trigram 分词（中文/子串友好）。
CREATE VIRTUAL TABLE IF NOT EXISTS utterance_fts USING fts5(
    text,
    content='utterance',
    content_rowid='id',
    tokenize='trigram'
);

-- 触发器：保持 FTS 索引与 utterance 同步。
CREATE TRIGGER IF NOT EXISTS utterance_ai AFTER INSERT ON utterance BEGIN
    INSERT INTO utterance_fts(rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS utterance_ad AFTER DELETE ON utterance BEGIN
    INSERT INTO utterance_fts(utterance_fts, rowid, text)
        VALUES ('delete', old.id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS utterance_au AFTER UPDATE ON utterance BEGIN
    INSERT INTO utterance_fts(utterance_fts, rowid, text)
        VALUES ('delete', old.id, old.text);
    INSERT INTO utterance_fts(rowid, text) VALUES (new.id, new.text);
END;
