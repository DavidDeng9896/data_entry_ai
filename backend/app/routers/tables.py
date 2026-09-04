"""结果表 CRUD 接口：列表/详情/新建（一步含列）/更新/删除/复制；建表 AI 对话"""
import asyncio
import json
import queue

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .. import database as db
from ..schemas import SchemaChatRequest
from ..services.ai_service import friendly_llm_error
from ..services.schema_chat import run_schema_chat

router = APIRouter(prefix="/api/tables", tags=["tables"])

_SSE_PADDING = ":" + (" " * 2048) + "\n\n"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _run_schema(req: SchemaChatRequest, on_progress=None) -> dict:
    return run_schema_chat(
        messages=req.messages,
        file_ids=req.file_ids,
        name=req.name or "",
        description=req.description or "",
        columns=req.columns,
        skill_name=req.skill_name or "",
        skill_md=req.skill_md or "",
        on_progress=on_progress,
    )


class ColumnIn(BaseModel):
    field: str
    title: str
    type: str = "text"
    required: bool = False
    options: list[str] = []
    description: str = ""


class TableCreate(BaseModel):
    name: str
    description: str = ""
    columns: list[ColumnIn] = []


class TableUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ColumnsUpdate(BaseModel):
    columns: list[ColumnIn]


class ImportCommit(BaseModel):
    rows: list[dict]
    source_files: list[str] = []
    skill_name: str = ""
    conflicts: list[dict] = []


@router.get("")
def list_tables():
    return db.list_tables()


@router.post("/schema/chat")
def schema_chat(req: SchemaChatRequest):
    try:
        return _run_schema(req)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e)) from e
    except Exception as e:
        raise HTTPException(500, friendly_llm_error(e)) from e


@router.post("/schema/chat/stream")
async def schema_chat_stream(req: SchemaChatRequest):
    async def gen():
        yield _SSE_PADDING
        yield _sse("step", {"text": "已连接，开始处理…"})
        last = ""
        for m in reversed(req.messages or []):
            if getattr(m, "role", None) == "user" and (m.content or "").strip():
                last = m.content.strip()
                break
        from ..services.schema_intent import classify_schema_intent
        intent = classify_schema_intent(last, has_files=bool(req.file_ids))
        if intent == "chat":
            yield _sse("step", {"text": "正在理解你的问题…", "intent": intent})
        elif req.file_ids:
            yield _sse("step", {"text": "正在解析附件…", "intent": intent})
        else:
            yield _sse("step", {"text": "正在根据描述设计列…", "intent": intent})
        progress_q: queue.Queue = queue.Queue()

        def on_progress(text: str):
            progress_q.put(text)

        try:
            task = asyncio.create_task(asyncio.to_thread(_run_schema, req, on_progress))
            while not task.done():
                while True:
                    try:
                        yield _sse("step", {"text": progress_q.get_nowait(), "intent": intent})
                    except queue.Empty:
                        break
                yield ": keepalive\n\n"
                yield _sse("ping", {})
                try:
                    await asyncio.wait_for(asyncio.shield(task), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
            while True:
                try:
                    yield _sse("step", {"text": progress_q.get_nowait(), "intent": intent})
                except queue.Empty:
                    break
            yield _sse("done", task.result())
        except Exception as e:
            yield _sse("error", {"message": friendly_llm_error(e)})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{table_id}")
def get_table(table_id: int):
    table = db.get_table(table_id)
    if not table:
        raise HTTPException(404, "结果表不存在")
    table["columns"] = db.get_columns(table_id)
    return table


@router.post("")
def create_table(body: TableCreate):
    if not body.name.strip():
        raise HTTPException(400, "表名不能为空")
    if not body.columns:
        raise HTTPException(400, "至少需要配置一列")
    try:
        return db.create_table(body.name.strip(), body.description.strip(), [c.model_dump() for c in body.columns])
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.put("/{table_id}")
def update_table(table_id: int, body: TableUpdate):
    try:
        db.update_table(table_id, body.name, body.description)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{table_id}")
def delete_table(table_id: int):
    db.delete_table(table_id)
    return {"ok": True}


@router.post("/{table_id}/copy")
def copy_table(table_id: int, body: TableUpdate):
    if not body.name or not body.name.strip():
        raise HTTPException(400, "新表名不能为空")
    try:
        return db.copy_table(table_id, body.name.strip())
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{table_id}/columns")
def get_columns(table_id: int):
    return db.get_columns(table_id)


@router.put("/{table_id}/columns")
def save_columns(table_id: int, body: ColumnsUpdate):
    try:
        db.save_columns(table_id, [c.model_dump() for c in body.columns])
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{table_id}/imports")
def commit_import(table_id: int, body: ImportCommit):
    try:
        return db.commit_import(
            table_id,
            body.rows,
            source_files=body.source_files,
            skill_name=body.skill_name,
            conflicts=body.conflicts,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{table_id}/imports")
def list_imports(table_id: int):
    if not db.get_table(table_id):
        raise HTTPException(404, "结果表不存在")
    return db.list_import_batches(table_id)


@router.get("/{table_id}/rows")
def list_rows(table_id: int):
    if not db.get_table(table_id):
        raise HTTPException(404, "结果表不存在")
    return db.list_imported_rows(table_id)
