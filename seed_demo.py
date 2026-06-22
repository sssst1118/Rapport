"""造一份 M3 演示数据，写入独立的 data/demo.db（不动 data/rapport.db）。

覆盖 M3 各界面所需：多人 / 跨天多段对话 / 多说话人 / 含未映射说话人 /
三类标注，音频统一指向已有的 data/sample.wav（时间码为示意，足以验证 🔊 机制）。

跑法：
    .venv/Scripts/python.exe seed_demo.py
然后让后端以该库启动：
    RAPPORT_DB_PATH=data/demo.db rapport serve
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from rapport.storage.db import Database

REPO = Path(__file__).resolve().parent
DEMO_DB = REPO / "data" / "demo.db"
SAMPLE_AUDIO = "data/sample.wav"  # 相对仓库根，演示用统一音频


def _set_started_at(db: Database, conv_id: int, when: datetime) -> None:
    """覆盖对话的 started_at（schema 默认 now，演示需要指定日期）。"""
    db._conn.execute(
        "UPDATE conversation SET started_at = ? WHERE id = ?",
        (when.strftime("%Y-%m-%d %H:%M:%S"), conv_id),
    )
    db._conn.commit()


def _add_line(
    db: Database,
    conv_id: int,
    *,
    label: str,
    text: str,
    start_ms: int,
    end_ms: int,
    person_id: int | None = None,
) -> int:
    return db.add_utterance(
        conv_id,
        text=text,
        speaker_label=label,
        person_id=person_id,
        start_ms=start_ms,
        end_ms=end_ms,
    )


def build() -> None:
    if DEMO_DB.exists():
        DEMO_DB.unlink()
    db = Database(DEMO_DB)

    today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    three_days = today - timedelta(days=3)

    # ---- 人物 ----
    me = db.add_person("我", relation="自己")
    wang = db.add_person("老王", relation="同事 · 直属上级")
    li = db.add_person("小李", relation="我带的实习生")
    linxi = db.add_person("林夕", relation="在一起的人")
    mom = db.add_person("妈妈", relation="家人")

    # ---- 今天 · 和老王的午饭（已映射，含标注）----
    c1 = db.add_conversation(audio_path=SAMPLE_AUDIO, note="午饭时聊到下季度规划")
    _set_started_at(db, c1, today.replace(hour=12, minute=20))
    t = 0
    def step(ms: int) -> tuple[int, int]:
        nonlocal t
        s = t; t += ms; return s, t
    s, e = step(3200); u_plan = _add_line(db, c1, label="B", person_id=wang, text="下个季度那个项目，我想让你来牵头。", start_ms=s, end_ms=e)
    s, e = step(2600); _add_line(db, c1, label="A", person_id=me, text="可以啊，不过人手够吗？", start_ms=s, end_ms=e)
    s, e = step(4200); u_promise = _add_line(db, c1, label="B", person_id=wang, text="放心，我跟上面争取再加两个名额，月底前给你答复。", start_ms=s, end_ms=e)
    s, e = step(2800); _add_line(db, c1, label="A", person_id=me, text="那行，我先把方案草稿出一版。", start_ms=s, end_ms=e)
    s, e = step(3600); _add_line(db, c1, label="B", person_id=wang, text="对了，上次那个客户的事，你别太往心里去，不怪你。", start_ms=s, end_ms=e)
    db.add_annotation(u_plan, type="tag", value="重要")
    db.add_annotation(u_promise, type="tag", value="待办")
    db.add_annotation(u_promise, type="note", value="老王说会争取名额——记下来，月底跟进。")

    # ---- 今天 · 晚上和林夕（已映射，轻松）----
    c2 = db.add_conversation(audio_path=SAMPLE_AUDIO, note="晚上散步")
    _set_started_at(db, c2, today.replace(hour=21, minute=5))
    t = 0
    s, e = step(2400); _add_line(db, c2, label="A", person_id=me, text="今天加班到挺晚的。", start_ms=s, end_ms=e)
    s, e = step(3000); u_x = _add_line(db, c2, label="B", person_id=linxi, text="我看出来了，你说话都没什么力气。早点回吧？", start_ms=s, end_ms=e)
    s, e = step(2200); _add_line(db, c2, label="A", person_id=me, text="再走一会儿，难得。", start_ms=s, end_ms=e)
    s, e = step(2800); _add_line(db, c2, label="B", person_id=linxi, text="周末我想去看那个展，你有空吗。", start_ms=s, end_ms=e)
    db.add_annotation(u_x, type="note", value="她其实是在关心我，但我当时只顾着累。")

    # ---- 昨天 · 妈妈电话（已映射）----
    c3 = db.add_conversation(audio_path=SAMPLE_AUDIO, note="妈妈来电")
    _set_started_at(db, c3, yesterday.replace(hour=19, minute=30))
    t = 0
    s, e = step(3000); _add_line(db, c3, label="B", person_id=mom, text="最近吃饭规律吗，别老点外卖。", start_ms=s, end_ms=e)
    s, e = step(2400); _add_line(db, c3, label="A", person_id=me, text="还行妈，你们身体怎么样。", start_ms=s, end_ms=e)
    s, e = step(3200); _add_line(db, c3, label="B", person_id=mom, text="都好，你爸血压稳住了。你下个月回来不。", start_ms=s, end_ms=e)

    # ---- 三天前 · 和小李 1on1（故意全部未映射，演示「A/B→真人」快速映射）----
    c4 = db.add_conversation(audio_path=SAMPLE_AUDIO, note="周会后单独聊（说话人待确认）")
    _set_started_at(db, c4, three_days.replace(hour=16, minute=0))
    t = 0
    s, e = step(3400); _add_line(db, c4, label="A", text="这周的任务我有点跟不上，想跟你说一下。", start_ms=s, end_ms=e)
    s, e = step(2600); _add_line(db, c4, label="B", text="没事，具体卡在哪了？", start_ms=s, end_ms=e)
    s, e = step(3800); _add_line(db, c4, label="A", text="那个接口文档我看不太懂，又不太敢一直问你。", start_ms=s, end_ms=e)
    s, e = step(3000); _add_line(db, c4, label="B", text="该问就问，这不丢人。我们约个固定时间过一遍。", start_ms=s, end_ms=e)

    counts = {
        "person": len(db.list_persons()),
        "conversation": len(db.list_conversations()),
    }
    db.close()
    print(f"演示库已生成：{DEMO_DB}")
    print(f"  人物 {counts['person']}，对话 {counts['conversation']}")
    print("启动后端：RAPPORT_DB_PATH=data/demo.db .venv/Scripts/python.exe -m rapport serve")


if __name__ == "__main__":
    build()
