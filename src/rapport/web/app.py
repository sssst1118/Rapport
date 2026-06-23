"""FastAPI 应用工厂与全部 /api 路由。

设计原则（对齐产品硬原则「事实与解读分离」）：
- 事实端点（人物、对话、话语、改写）直接读写存储层，确定、可复现。
- 解读端点（摘要、人物分析、brief、划选分析）一律返回 200 + 统一「pending_m4」
  信封，绝不报错；M4 接入按需分析后再填充 data。

app 工厂签名：create_app(db=None, db_path=None, repo_root=None)
- 传 db：直接复用调用方的 Database（测试注入内存库的首选）。
- 传 db_path：按路径开库，应用关闭时由本模块负责 close。
- 都不传：用 config.DB_PATH 开库（serve 子命令的默认路径）。
- repo_root：解析对话 audio_path（相对仓库根）与定位 frontend/dist 的基准目录；
  缺省取仓库根（本文件上溯到 src/rapport/web 的三级父目录）。
"""

from __future__ import annotations

import sqlite3
import threading
from concurrent.futures import Future
from contextlib import asynccontextmanager
from pathlib import Path
from queue import Queue
from typing import Any, Callable, TypeVar

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel

from .._frozen import is_frozen, resource_root
from ..analysis import AnalysisError, get_provider
from ..analysis import analyze as _analyze
from ..mcp.tools import build_graph
from ..storage.db import Database

# 资源根：定位随包的 frontend/dist。开发态 = 仓库根（本文件上溯四级一致），
# 冻结态 = sys._MEIPASS（PyInstaller 把 frontend/dist 解包于此）。统一由
# _frozen.resource_root() 决定，避免打包后 parents[N] 失效。
_REPO_ROOT = resource_root()

_T = TypeVar("_T")


class _DbThread:
    """把一个 SQLite Database 线程封闭到单个专属工作线程上。

    存储层连接默认不允许跨线程使用（check_same_thread=True，且 db.py 已冻结
    不能改），而 FastAPI/Starlette 的路由处理器跑在事件循环的线程池里、线程随机。
    本类用「单工作线程 + 任务队列」把所有 db 调用串行投递到同一个线程执行，
    既满足 SQLite 的同线程要求，也天然把并发请求对同一连接的访问串行化（demo
    量级下完全够用）。

    connect 必须在该工作线程内完成（连接「归属」创建它的线程），因此本类接受一个
    无参工厂，在工作线程里调用它来建立 Database。
    """

    def __init__(self, factory: Callable[[], Database]) -> None:
        self._tasks: Queue = Queue()
        self._db: Database | None = None
        self._ready = threading.Event()
        self._error: BaseException | None = None
        self._thread = threading.Thread(
            target=self._run, args=(factory,), daemon=True, name="rapport-db"
        )
        self._thread.start()
        self._ready.wait()
        if self._error is not None:
            raise self._error

    def _run(self, factory: Callable[[], Database]) -> None:
        try:
            self._db = factory()
        except BaseException as exc:  # noqa: BLE001
            self._error = exc
            self._ready.set()
            return
        self._ready.set()
        while True:
            item = self._tasks.get()
            if item is None:  # 收到关闭信号
                break
            fn, future = item
            try:
                future.set_result(fn(self._db))
            except BaseException as exc:  # noqa: BLE001
                future.set_exception(exc)

    def call(self, fn: Callable[[Database], _T]) -> _T:
        """在工作线程上执行 fn(db) 并同步返回其结果（异常原样抛回）。"""
        future: Future = Future()
        self._tasks.put((fn, future))
        return future.result()

    def close(self) -> None:
        """关闭底层连接并停止工作线程。"""
        def _shut(db: Database) -> None:
            db.close()

        try:
            self.call(_shut)
        finally:
            self._tasks.put(None)


class _DbProxy:
    """对外表现得像 Database，但把每个方法调用投递到 _DbThread 的工作线程。

    路由代码因此可以照常写 `db.list_persons()`，无需感知线程封闭的存在。
    另外提供 delete_annotation（db.py 无此公共方法，按契约在 web 层直接对连接
    执行 DELETE）。
    """

    def __init__(self, dbthread: _DbThread) -> None:
        self._dbthread = dbthread

    def __getattr__(self, name: str) -> Callable[..., Any]:
        def method(*args: Any, **kwargs: Any) -> Any:
            return self._dbthread.call(
                lambda d: getattr(d, name)(*args, **kwargs)
            )

        return method

    def delete_annotation(self, annotation_id: int) -> None:
        """删除一条标注（db.py 无对应公共方法，直接对连接执行 DELETE）。"""
        def _do(d: Database) -> None:
            d._conn.execute(
                "DELETE FROM annotation WHERE id = ?", (annotation_id,)
            )
            d._conn.commit()

        self._dbthread.call(_do)

    def get_utterance(self, utterance_id: int) -> Any:
        """按 id 取单条话语行（db.py 无对应公共方法，按只读 SQL 在工作线程内取）。

        analysis 层做引用解析时要按 utterance_id 回查整行；db 连接被线程封闭，
        不能从路由线程直接碰 _conn，故在工作线程里执行查询。
        """
        def _do(d: Database) -> Any:
            return d._conn.execute(
                "SELECT * FROM utterance WHERE id = ?", (utterance_id,)
            ).fetchone()

        return self._dbthread.call(_do)


# ---- 请求体模型 ----------------------------------------------------------


class PersonCreate(BaseModel):
    """新建人物请求体。"""

    name: str
    relation: str | None = None


class UtteranceTextUpdate(BaseModel):
    """改话语文字请求体。"""

    text: str


class UtterancePersonUpdate(BaseModel):
    """改话语归属请求体（person_id 可为 null 表示取消归属）。"""

    person_id: int | None = None


class RelabelBody(BaseModel):
    """整段说话人快速映射请求体。"""

    speaker_label: str
    person_id: int | None = None


class AnnotationCreate(BaseModel):
    """新增标注请求体（type 取 'tag' | 'note'）。"""

    type: str
    value: str | None = None


class AnalyzeBody(BaseModel):
    """划选分析请求体。"""

    utterance_ids: list[int] = []


class ReviewBody(BaseModel):
    """复盘请求体。scope 取 'conversation' | 'person' | 'day'。"""

    scope: str
    id: int | None = None


# ---- 解读信封（M4） -----------------------------------------------------
#
# 统一 Interpretation 信封（前端已冻结该类型）三态：
# - needs_setup：未配置语言模型；
# - ready：成功，data 带 {overview, findings:[{point, quotes:[Citation...]}]}；
# - error：分析失败（AnalysisError），HTTP 仍 200，绝不 500。

_NEEDS_SETUP_MSG = (
    "未配置语言模型。设置 ANTHROPIC_API_KEY 并令 RAPPORT_LLM_PROVIDER=anthropic "
    "即可启用解读（或 =fake 看示例）。"
)


def _needs_setup() -> dict[str, Any]:
    """未配置 provider 时的统一信封。"""
    return {
        "kind": "interpretation",
        "status": "needs_setup",
        "message": _NEEDS_SETUP_MSG,
        "data": None,
    }


def _ready(data: dict[str, Any]) -> dict[str, Any]:
    """成功信封。data = {overview, findings:[{point, quotes:[Citation...]}]}。"""
    return {
        "kind": "interpretation",
        "status": "ready",
        "message": "",
        "data": data,
    }


def _error(message: str) -> dict[str, Any]:
    """失败信封（中文原因）；HTTP 仍 200，绝不 500。"""
    return {
        "kind": "interpretation",
        "status": "error",
        "message": message,
        "data": None,
    }


def _interpret(
    db: Database,
    fn: Callable[..., dict[str, Any]],
    *args: Any,
    lang: str = "zh",
) -> dict[str, Any]:
    """跑一次按需分析并裹成 Interpretation 信封，吸收三态。

    provider 经 get_provider() 取（每次取，故配置/测试 monkeypatch 即时生效）：
    None → needs_setup；成功 → ready；AnalysisError → error（不 500）。
    lang 跟随界面语言（"en"/"zh"），让解读输出语言与界面一致。
    """
    provider = get_provider()
    if provider is None:
        return _needs_setup()
    try:
        data = fn(db, provider, *args, lang=lang)
    except AnalysisError as exc:
        return _error(str(exc))
    return _ready(data)


# ---- 组合查询（web 层用现有 db 方法拼，不改 db.py） ----------------------


def _utterance_count(db: Database, person_id: int) -> int:
    """某人的话语总数。"""
    return len(db.get_utterances_for_person(person_id))


def _person_brief(row: sqlite3.Row) -> dict[str, Any]:
    """人物列表/参与者用的精简表示。"""
    return {"id": row["id"], "name": row["name"]}


def _speakers_in(db: Database, conversation_id: int) -> list[str]:
    """对话内去重的 speaker_label（按首次出现顺序，过滤空标签）。"""
    seen: list[str] = []
    for u in db.get_utterances(conversation_id):
        label = u["speaker_label"]
        if label and label not in seen:
            seen.append(label)
    return seen


def create_app(
    db: Database | None = None,
    db_path: str | Path | None = None,
    repo_root: str | Path | None = None,
    status_path: str | Path | None = None,
) -> FastAPI:
    """构建并返回 FastAPI 应用。

    数据库的线程封闭：无论哪种注入方式，最终都包成 _DbProxy，所有 db 调用统一
    串行投递到一个专属工作线程执行——因为 SQLite 连接默认不允许跨线程，而路由跑
    在随机线程池里。

    Args:
        db: 直接注入的 Database；其连接将被移交到工作线程串行使用（注入方此后
            不应再从别的线程直接用它）。本模块负责在应用关闭时 close 它。
        db_path: 数据库文件路径；本模块在工作线程内开库，关闭时 close。
            测试推荐用这种方式：先在测试线程用自己的 Database 把数据写进同一个
            文件，再把路径传进来，避免跨线程共享同一连接。
        repo_root: 解析对话 audio_path（相对基准）的目录；缺省取资源根。
            注意 frontend/dist 始终从资源根（冻结态 = bundle）取，不受此参数影响——
            前端是只读随包资源，而 audio 是可写用户数据，两者在冻结态分属不同根。
        status_path: 录制状态文件路径（rapport watch 守护进程原子写、本端点读）；
            缺省取 config.RECORDING_STATUS_PATH。

    Returns:
        配置好全部路由的 FastAPI 实例。
    """
    if db is not None:
        factory: Callable[[], Database] = lambda: db  # noqa: E731
    else:
        if db_path is None:
            from .. import config

            db_path = config.DB_PATH
        _path = db_path
        factory = lambda: Database(_path)  # noqa: E731

    dbthread = _DbThread(factory)
    db = _DbProxy(dbthread)  # type: ignore[assignment]

    root = Path(repo_root) if repo_root is not None else _REPO_ROOT
    # frontend/dist 的基准：
    # - 冻结态：始终从资源根（sys._MEIPASS 解包目录）取——前端是只读随包资源，
    #   与 audio 的可写根（repo_root 参数所指）解耦。
    # - 非冻结态：尊重显式传入的 repo_root（开发/测试可注入临时目录控制 dist 有无），
    #   缺省回退资源根（= 仓库根）。
    if is_frozen():
        dist_base = resource_root()
    else:
        dist_base = root
    dist_dir = dist_base / "frontend" / "dist"

    if status_path is not None:
        _status_path = Path(status_path)
    else:
        from .. import config

        _status_path = config.RECORDING_STATUS_PATH

    @asynccontextmanager
    async def lifespan(_app: FastAPI):  # pragma: no cover - 仅生命周期
        try:
            yield
        finally:
            dbthread.close()

    app = FastAPI(title="Rapport 后端", version="0.0.1", lifespan=lifespan)
    # 把依赖挂到 app.state，路由内直接取，避免全局可变状态。
    app.state.db = db
    app.state.repo_root = root

    # ---- 状态 -----------------------------------------------------------

    @app.get("/api/status")
    def get_status() -> dict[str, bool]:
        """读 rapport watch 守护进程写的录制状态文件，对外诚实暴露 {recording, paused}。

        文件不存在/损坏一律诚实回未录音，绝不抛 500（read_status 内已兜底）。
        """
        from ..alwayson.status import read_status

        return read_status(_status_path)

    # ---- 人物（事实） ---------------------------------------------------

    @app.get("/api/people")
    def list_people() -> list[dict[str, Any]]:
        """人物列表，按 list_persons 顺序，含话语数。"""
        out = []
        for p in db.list_persons():
            out.append(
                {
                    "id": p["id"],
                    "name": p["name"],
                    "avatar": p["avatar"],
                    "relation": p["relation"],
                    "utterance_count": _utterance_count(db, p["id"]),
                }
            )
        return out

    @app.post("/api/people")
    def create_person(body: PersonCreate) -> dict[str, Any]:
        """新建人物（用于把说话人映射到尚不存在的人）。"""
        pid = db.add_person(body.name, relation=body.relation)
        p = db.get_person(pid)
        return {
            "id": p["id"],
            "name": p["name"],
            "relation": p["relation"],
            "avatar": p["avatar"],
        }

    @app.get("/api/people/{person_id}")
    def get_person(person_id: int) -> dict[str, Any]:
        """人物详情，含对话数与话语数；缺失 404。"""
        p = db.get_person(person_id)
        if p is None:
            raise HTTPException(status_code=404, detail="人物不存在")
        utterances = db.get_utterances_for_person(person_id)
        conv_ids = {u["conversation_id"] for u in utterances}
        return {
            "id": p["id"],
            "name": p["name"],
            "avatar": p["avatar"],
            "relation": p["relation"],
            "created_at": p["created_at"],
            "updated_at": p["updated_at"],
            "conversation_count": len(conv_ids),
            "utterance_count": len(utterances),
        }

    @app.get("/api/people/{person_id}/utterances")
    def person_utterances(person_id: int) -> list[dict[str, Any]]:
        """某人跨全部对话的话语，最近优先（供「对话历史」）。"""
        if db.get_person(person_id) is None:
            raise HTTPException(status_code=404, detail="人物不存在")
        # 缓存对话信息，避免对每句重复查库。
        conv_cache: dict[int, sqlite3.Row | None] = {}

        def conv(cid: int) -> sqlite3.Row | None:
            if cid not in conv_cache:
                conv_cache[cid] = db.get_conversation(cid)
            return conv_cache[cid]

        rows = []
        for u in db.get_utterances_for_person(person_id):
            c = conv(u["conversation_id"])
            rows.append(
                {
                    "id": u["id"],
                    "conversation_id": u["conversation_id"],
                    "conversation_note": c["note"] if c else None,
                    "started_at": c["started_at"] if c else None,
                    "speaker_label": u["speaker_label"],
                    "text": u["text"],
                    "start_ms": u["start_ms"],
                    "end_ms": u["end_ms"],
                }
            )
        # 最近优先：按对话 started_at 倒序，同对话内按 start_ms 升序（保留时间线）。
        rows.sort(key=lambda r: (r["started_at"] or "", -r["start_ms"]), reverse=True)
        return rows

    @app.get("/api/people/{person_id}/analysis")
    def person_analysis(person_id: int, lang: str = "zh") -> dict[str, Any]:
        """人物分析：该人跨对话话语 → 沟通风格/在意什么/承诺待办（带原话出处）。"""
        return _interpret(db, _analyze.analyze_person, person_id, lang=lang)

    @app.get("/api/people/{person_id}/brief")
    def person_brief(person_id: int, lang: str = "zh") -> dict[str, Any]:
        """见面前 brief：该人跨对话话语 → 下次见面前该记得什么（带原话出处）。"""
        return _interpret(db, _analyze.meeting_brief, person_id, lang=lang)

    # ---- 对话（事实） ---------------------------------------------------

    @app.get("/api/conversations")
    def list_conversations() -> list[dict[str, Any]]:
        """对话列表，最近优先，含参与者与话语数。"""
        out = []
        for c in db.list_conversations():
            utterances = db.get_utterances(c["id"])
            participants = [
                _person_brief(p) for p in db.get_persons_in_conversation(c["id"])
            ]
            out.append(
                {
                    "id": c["id"],
                    "started_at": c["started_at"],
                    "note": c["note"],
                    "has_audio": bool(c["audio_path"]),
                    "utterance_count": len(utterances),
                    "participants": participants,
                }
            )
        return out

    @app.get("/api/conversations/{conversation_id}")
    def get_conversation(conversation_id: int) -> dict[str, Any]:
        """对话详情，含话语、标注、去重说话人、参与者；缺失 404。"""
        c = db.get_conversation(conversation_id)
        if c is None:
            raise HTTPException(status_code=404, detail="对话不存在")
        utterances = []
        for u in db.get_utterances(conversation_id):
            anns = [
                {"id": a["id"], "type": a["type"], "value": a["value"]}
                for a in db.get_annotations(u["id"])
            ]
            utterances.append(
                {
                    "id": u["id"],
                    "person_id": u["person_id"],
                    "speaker_label": u["speaker_label"],
                    "text": u["text"],
                    "start_ms": u["start_ms"],
                    "end_ms": u["end_ms"],
                    "annotations": anns,
                }
            )
        participants = [
            _person_brief(p)
            for p in db.get_persons_in_conversation(conversation_id)
        ]
        return {
            "id": c["id"],
            "started_at": c["started_at"],
            "note": c["note"],
            "has_audio": bool(c["audio_path"]),
            "participants": participants,
            "speakers": _speakers_in(db, conversation_id),
            "utterances": utterances,
        }

    @app.get("/api/conversations/{conversation_id}/summary")
    def conversation_summary(
        conversation_id: int, lang: str = "zh"
    ) -> dict[str, Any]:
        """顶部摘要：该对话全部话语 → 聊了什么/关键结论/跟进（带原话出处）。"""
        return _interpret(
            db, _analyze.summarize_conversation, conversation_id, lang=lang
        )

    @app.get("/api/conversations/{conversation_id}/audio")
    def conversation_audio(conversation_id: int, request: Request) -> Response:
        """按 audio_path 流式返回音频，支持 HTTP Range（206 + Content-Range）。"""
        c = db.get_conversation(conversation_id)
        if c is None or not c["audio_path"]:
            raise HTTPException(status_code=404, detail="该对话没有音频")
        audio_path = (root / c["audio_path"]).resolve()
        if not audio_path.is_file():
            raise HTTPException(status_code=404, detail="音频文件不存在")
        return _serve_audio(audio_path, request)

    @app.post("/api/conversations/{conversation_id}/relabel")
    def relabel(conversation_id: int, body: RelabelBody) -> dict[str, int]:
        """§9.1 快速映射：对话内某说话人标签的全部话语一次性归属，返回条数。"""
        n = db.relabel_speaker(conversation_id, body.speaker_label, body.person_id)
        return {"updated": n}

    # ---- 改写（事实） ---------------------------------------------------

    @app.patch("/api/utterances/{utterance_id}")
    def patch_utterance(
        utterance_id: int, body: UtteranceTextUpdate
    ) -> dict[str, bool]:
        """改话语文字。"""
        db.update_utterance_text(utterance_id, body.text)
        return {"ok": True}

    @app.patch("/api/utterances/{utterance_id}/person")
    def patch_utterance_person(
        utterance_id: int, body: UtterancePersonUpdate
    ) -> dict[str, bool]:
        """改话语归属（person_id 可为 null 取消归属）。"""
        db.set_utterance_person(utterance_id, body.person_id)
        return {"ok": True}

    @app.post("/api/utterances/{utterance_id}/annotations")
    def add_annotation(
        utterance_id: int, body: AnnotationCreate
    ) -> dict[str, Any]:
        """给话语加一条标注（tag / note）。"""
        aid = db.add_annotation(utterance_id, type=body.type, value=body.value)
        return {"id": aid, "type": body.type, "value": body.value}

    @app.delete("/api/annotations/{annotation_id}")
    def delete_annotation(annotation_id: int) -> dict[str, bool]:
        """删除一条标注（db.py 无对应公共方法，web 层直接对连接执行 DELETE）。"""
        db.delete_annotation(annotation_id)
        return {"ok": True}

    # ---- 解读：划选分析 -------------------------------------------------

    @app.post("/api/analyze")
    def analyze(body: AnalyzeBody, lang: str = "zh") -> dict[str, Any]:
        """划选几行 → 就事论事的解读（带原话出处）。"""
        return _interpret(
            db, _analyze.analyze_selection, body.utterance_ids, lang=lang
        )

    # ---- 关系图（事实：人物 + 共现推断的连线） --------------------------

    @app.get("/api/graph")
    def graph() -> dict[str, Any]:
        """关系网络：节点=人物，连线=同一段对话同时在场 → 推断彼此认识（§10.5）。

        连线权重 = 两人共同在场的对话数；每个节点带话语数/对话数，供前端按互动量
        定节点大小、按连线粗细表达亲密/新近。这是从真实记录里「白捡」的关系，
        不是模型脑补——属事实层。

        构图逻辑下沉到 rapport.mcp.tools.build_graph，与 MCP relationship_graph 工具共享
        （build_graph 只调用只读方法，经 _DbProxy 照样可用），避免 web 与 mcp 两处重复。
        """
        return build_graph(db)

    # ---- 解读：复盘（M4 占位） ------------------------------------------

    @app.post("/api/review")
    def review(body: ReviewBody, lang: str = "zh") -> dict[str, Any]:
        """复盘的『你的视角 / 对方视角 / 接下来怎么做』（带原话出处）。

        事实回放（第①步）由前端复用对话/话语真数据呈现，无需此端点。
        """
        return _interpret(db, _analyze.review, body.scope, body.id, lang=lang)

    # ---- 静态托管（SPA，history fallback） ------------------------------

    _mount_static(app, dist_dir)

    return app


# ---- 音频 Range 处理 -----------------------------------------------------


def _serve_audio(path: Path, request: Request) -> Response:
    """返回音频，支持单段 Range；无 Range 时 200 全量并声明 Accept-Ranges。"""
    file_size = path.stat().st_size
    range_header = request.headers.get("range")

    if range_header is None:
        return FileResponse(
            path,
            media_type="audio/wav",
            headers={"Accept-Ranges": "bytes"},
        )

    start, end = _parse_range(range_header, file_size)
    if start is None:
        # 不可满足的 Range：416。
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    length = end - start + 1
    with open(path, "rb") as f:
        f.seek(start)
        data = f.read(length)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Content-Length": str(length),
    }
    return Response(
        content=data,
        status_code=206,
        media_type="audio/wav",
        headers=headers,
    )


def _parse_range(
    range_header: str, file_size: int
) -> tuple[int | None, int | None]:
    """解析 `bytes=start-end`（单段），返回 (start, end) 闭区间，或 (None, None) 不可满足。"""
    unit, _, spec = range_header.partition("=")
    if unit.strip().lower() != "bytes":
        return None, None
    spec = spec.split(",")[0].strip()  # 只取第一段
    start_s, _, end_s = spec.partition("-")
    try:
        if start_s == "":
            # 后缀字节：bytes=-N → 末尾 N 字节
            n = int(end_s)
            if n <= 0:
                return None, None
            start = max(file_size - n, 0)
            end = file_size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else file_size - 1
    except ValueError:
        return None, None
    if start > end or start >= file_size:
        return None, None
    end = min(end, file_size - 1)
    return start, end


# ---- 静态托管 ------------------------------------------------------------


def _mount_static(app: FastAPI, dist_dir: Path) -> None:
    """把 frontend/dist 作为 SPA 托管在根路径；缺失时给友好提示而非崩溃。

    用一个 catch-all GET 路由实现 history fallback：命中真实文件就返回文件，
    否则回落到 index.html（SPA 前端路由）。/api 路由已在前面注册，优先级更高。
    """
    index_html = dist_dir / "index.html"

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> Response:
        if not index_html.is_file():
            return HTMLResponse(
                "<h1>Rapport</h1><p>前端尚未构建，请先在 frontend/ 下执行 "
                "<code>npm run build</code>。</p>",
                status_code=200,
            )
        # 防目录穿越：把请求路径限制在 dist_dir 内。
        candidate = (dist_dir / full_path).resolve()
        try:
            candidate.relative_to(dist_dir.resolve())
        except ValueError:
            candidate = index_html
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_html)
