"""AI 识别接口：上传文件 → 识别填入表格"""
import asyncio
import json
import queue

from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from .. import database as db
from ..schemas import RecognizeRequest, ChatRequest
from ..services import file_parser, ai_service
from ..services.ai_service import friendly_llm_error
from ..services.intent import classify_intent
from ..services.skill_matcher import resolve_skill
from ..services.row_merge import compose_extraction_reply, merge_extracted_rows

router = APIRouter(prefix="/api/recognize", tags=["recognize"])


def _resolve_file_ids(req: ChatRequest) -> list[str]:
    ids: list[str] = []
    if req.file_id:
        ids.append(req.file_id)
    for fid in req.file_ids or []:
        if fid and fid not in ids:
            ids.append(fid)
    return ids


def _parse_max_chars() -> int:
    try:
        return int(db.load_model_settings().get("parse_max_chars") or 0)
    except (TypeError, ValueError):
        return 0


def _load_file_items(file_ids: list[str]) -> list[dict]:
    items: list[dict] = []
    if not file_ids:
        return items
    max_chars = _parse_max_chars()
    for fid in file_ids:
        try:
            label = file_parser.original_filename(fid)
            if file_parser.is_image(fid):
                text = f"### 文件: {label}\n（已上传图片，当前以文本模式处理）"
                items.append({
                    "file_id": fid, "label": label, "text": text,
                    "chars": len(text), "truncated": False,
                })
                continue
            text = file_parser.parse_to_text(fid, max_chars=max_chars)
            wrapped = f"### 文件: {label}\n{text}"
            items.append({
                "file_id": fid,
                "label": label,
                "text": wrapped,
                "chars": len(text),
                "truncated": "已截断" in text,
            })
        except FileNotFoundError as e:
            raise HTTPException(404, str(e)) from e
    return items


def _load_files_content(file_ids: list[str]) -> tuple[str | None, dict]:
    items = _load_file_items(file_ids)
    meta = {
        "count": len(file_ids),
        "chars": sum(i["chars"] for i in items),
        "truncated": any(i["truncated"] for i in items),
    }
    if not items:
        return None, meta
    return "\n\n---\n\n".join(f"### {i['file_id']}\n{i['text']}" for i in items), meta


def _last_user_text(messages) -> str:
    for m in reversed(messages or []):
        if getattr(m, "role", None) == "user" and (m.content or "").strip():
            return m.content.strip()
    return ""


def _skill_meta_payload(resolved: dict) -> dict:
    return {
        "skill_id": resolved.get("skill_id"),
        "skill_name": resolved.get("skill_name"),
        "skill_auto": bool(resolved.get("skill_auto")),
        "skill_reason": resolved.get("skill_reason") or "",
    }


def _resolve_for_request(req: ChatRequest | RecognizeRequest, file_content: str | None, *, allow_auto: bool) -> dict:
    skills = db.list_skills_full()
    settings = db.load_model_settings()
    use_llm = (not settings.get("mock")) and bool((settings.get("text_model") or {}).get("api_key"))
    auto_skill = bool(getattr(req, "auto_skill", True)) if allow_auto else False
    table_name = getattr(req, "table_name", None) or ""
    return resolve_skill(
        skills,
        skill_id=req.skill_id,
        auto_skill=auto_skill,
        table_name=table_name,
        columns=req.columns,
        file_content=file_content or "",
        use_llm=use_llm,
        llm_cfg=settings.get("text_model") if use_llm else None,
    )


def _run_chat(req: ChatRequest) -> dict:
    file_ids = _resolve_file_ids(req)
    items = _load_file_items(file_ids)
    last = _last_user_text(req.messages)
    intent = classify_intent(last, has_files=bool(file_ids))
    file_meta = {
        "count": len(items),
        "chars": sum(i["chars"] for i in items),
        "truncated": any(i["truncated"] for i in items),
    }

    if intent == "chat":
        skill_content = db.get_skill_content(req.skill_id) if req.skill_id else None
        skill_row = db.get_skill(req.skill_id) if req.skill_id else None
        resolved = {
            "skill_id": req.skill_id,
            "skill_name": skill_row["name"] if skill_row else None,
            "skill_auto": False,
            "skill_reason": "问答轮次不自动匹配 Skill" if not req.skill_id else "用户指定",
            "skill_content": skill_content,
        }
        joined = "\n\n---\n\n".join(i["text"] for i in items) if items else None
        reply, rows = ai_service.chat(
            req.messages, req.columns, resolved.get("skill_content"), joined,
            intent=intent, file_meta=file_meta, table_name=req.table_name or "",
        )
        return {"reply": reply, "rows": rows, "intent": intent, "file_meta": file_meta, **_skill_meta_payload(resolved)}

    if not items:
        resolved = _resolve_for_request(req, "", allow_auto=True)
        reply, rows = ai_service.chat(
            req.messages, req.columns, resolved.get("skill_content"), None,
            intent=intent, file_meta=file_meta, table_name=req.table_name or "",
        )
        return {"reply": reply, "rows": rows, "intent": intent, "file_meta": file_meta, **_skill_meta_payload(resolved)}

    all_rows: list[dict] = []
    chunk_notes: list[tuple[str, list[dict]]] = []
    resolved_list: list[dict] = []
    resolved = _resolve_for_request(req, items[0]["text"], allow_auto=True)
    n = len(items)
    for i, item in enumerate(items, 1):
        resolved = _resolve_for_request(req, item["text"], allow_auto=True)
        resolved_list.append(resolved)
        reply, rows = ai_service.chat(
            req.messages, req.columns, resolved.get("skill_content"), item["text"],
            intent=intent,
            file_meta={"count": 1, "chars": item["chars"], "truncated": item["truncated"]},
            table_name=req.table_name or "",
        )
        label = item.get("label") or item["file_id"]
        sk = resolved.get("skill_name") or "基线"
        note = f"附件 {i}/{n}（{label}）：{sk}，抽出 {len(rows or [])} 行"
        if reply:
            note = f"{note}\n{reply}"
        chunk_notes.append((note, rows or []))
        all_rows.extend(rows or [])
    names = []
    for r in resolved_list:
        nme = r.get("skill_name")
        if nme and nme not in names:
            names.append(nme)
    meta = _skill_meta_payload(resolved)
    if n > 1:
        meta["skill_reason"] = "逐文件匹配 Skill 后合并行"
        meta["skill_name"] = "、".join(names) if names else meta.get("skill_name")
    raw_n = len(all_rows)
    all_rows, conflicts = merge_extracted_rows(all_rows, key_field="cpds_id")
    return {
        "reply": compose_extraction_reply(
            chunk_notes, all_rows, raw_n=raw_n, n_items=n, new_conflicts=conflicts,
        ),
        "rows": all_rows,
        "intent": intent,
        "file_meta": file_meta,
        **meta,
    }


async def _run_in_thread(fn, *args, **kwargs):
    task = asyncio.create_task(asyncio.to_thread(fn, *args, **kwargs))
    while not task.done():
        yield "ping", {}
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=10)
        except asyncio.TimeoutError:
            continue
    yield "result", task.result()


async def _run_chat_with_progress(*args, **kwargs):
    progress_q: queue.Queue = queue.Queue()

    def on_progress(text: str):
        progress_q.put(text)

    kwargs = {**kwargs, "on_progress": on_progress}
    task = asyncio.create_task(asyncio.to_thread(ai_service.chat, *args, **kwargs))
    while not task.done():
        had = False
        while True:
            try:
                yield "step", {"text": progress_q.get_nowait()}
                had = True
            except queue.Empty:
                break
        if not had:
            yield "ping", {}
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=1.0)
        except asyncio.TimeoutError:
            continue
    while True:
        try:
            yield "step", {"text": progress_q.get_nowait()}
        except queue.Empty:
            break
    yield "result", task.result()


async def _aiter_chat_events(req: ChatRequest):
    file_ids = _resolve_file_ids(req)
    last = _last_user_text(req.messages)
    intent = classify_intent(last, has_files=bool(file_ids))

    if intent == "chat":
        yield "step", {"text": "正在理解你的问题…", "intent": intent}
        result = None
        async for kind, payload in _run_in_thread(_run_chat, req):
            if kind == "ping":
                yield "ping", {}
            else:
                result = payload
        yield "done", {k: result[k] for k in ("reply", "rows", "intent", "skill_id", "skill_name", "skill_auto", "skill_reason")}
        return

    yield "step", {"text": "正在读取附件（大 Excel 解析可能要一会儿）…", "intent": intent}
    items = None
    async for kind, payload in _run_in_thread(_load_file_items, file_ids):
        if kind == "ping":
            yield "ping", {}
        else:
            items = payload
    items = items or []
    file_meta = {
        "count": len(items),
        "chars": sum(i["chars"] for i in items),
        "truncated": any(i["truncated"] for i in items),
    }
    n = len(items)
    yield "step", {"text": f"读取 {n} 个附件，将逐个识别后合并", "intent": intent}

    all_rows: list = []
    chunk_notes: list[tuple[str, list[dict]]] = []
    resolved_list: list[dict] = []
    resolved = {
        "skill_id": None, "skill_name": None, "skill_auto": True,
        "skill_reason": "", "skill_content": None,
    }
    for i, item in enumerate(items, 1):
        label = item.get("label") or item["file_id"]
        yield "step", {"text": f"附件 {i}/{n}：{label}"}
        resolved = await asyncio.to_thread(
            lambda it=item: _resolve_for_request(req, it["text"], allow_auto=True)
        )
        resolved_list.append(resolved)
        skill_txt = resolved.get("skill_name") or "仅基线"
        yield "step", {"text": f"附件 {i}/{n} 匹配 {skill_txt}（{item['chars']} 字）"}
        reply, rows = None, None
        async for kind, payload in _run_chat_with_progress(
            req.messages,
            req.columns,
            resolved.get("skill_content"),
            item["text"],
            intent=intent,
            file_meta={"count": 1, "chars": item["chars"], "truncated": item["truncated"]},
            table_name=req.table_name or "",
        ):
            if kind == "ping":
                yield "ping", {}
            elif kind == "step":
                yield "step", payload
            else:
                reply, rows = payload
        n_rows = len(rows or [])
        yield "step", {"text": f"附件 {i}/{n} 抽出 {n_rows} 行"}
        note = f"附件 {i}/{n}（{label}）"
        if reply:
            note = f"{note}：{reply}"
        chunk_notes.append((note, rows or []))
        all_rows.extend(rows or [])

    if not items:
        yield "step", {"text": "未指定模板，仅用基线", "intent": intent}
        async for kind, payload in _run_in_thread(
            ai_service.chat, req.messages, req.columns, None, None,
            intent=intent, file_meta=file_meta, table_name=req.table_name or "",
        ):
            if kind == "ping":
                yield "ping", {}
            else:
                chunk_notes.append((payload[0], payload[1] or []))
                all_rows.extend(payload[1] or [])

    raw_n = len(all_rows)
    all_rows, conflicts = merge_extracted_rows(all_rows, key_field="cpds_id")
    yield "step", {"text": f"合并完成 {len(all_rows)} 行"}
    names = []
    for r in resolved_list:
        nme = r.get("skill_name")
        if nme and nme not in names:
            names.append(nme)
    meta = _skill_meta_payload(resolved)
    if n > 1:
        meta["skill_reason"] = "逐文件匹配 Skill 后合并行"
        meta["skill_name"] = "、".join(names) if names else meta.get("skill_name")
    yield "done", {
        "reply": compose_extraction_reply(
            chunk_notes, all_rows, raw_n=raw_n, n_items=n, new_conflicts=conflicts,
        ),
        "rows": all_rows,
        "intent": intent,
        **meta,
    }


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/upload")
async def upload(file: UploadFile):
    content = await file.read()
    if not content:
        raise HTTPException(400, "文件为空")
    info = file_parser.save_upload(file.filename or "unnamed", content)
    return {"file_id": info["file_id"], "filename": info["filename"], "ext": info["ext"]}


@router.post("/run")
def run(req: RecognizeRequest):
    try:
        if file_parser.is_image(req.file_id):
            file_content, file_meta = None, {"count": 1, "chars": 0, "truncated": False}
        else:
            text = file_parser.parse_to_text(req.file_id, max_chars=_parse_max_chars())
            file_content, file_meta = text, {"count": 1, "chars": len(text), "truncated": "已截断" in text}
        resolved = _resolve_for_request(req, file_content or "", allow_auto=True)
        if file_parser.is_image(req.file_id):
            rows, message = ai_service.recognize_image(req.file_id, req.columns, resolved.get("skill_content"))
        else:
            if not (file_content or "").strip():
                return {"rows": [], "message": "未能从文件中解析出内容", **_skill_meta_payload(resolved)}
            rows, message = ai_service.recognize_text(
                file_content, req.columns, resolved.get("skill_content"),
                table_name=getattr(req, "table_name", None) or "",
            )
        return {"rows": rows, "message": message, **_skill_meta_payload(resolved)}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"识别失败：{str(e)[:300]}")


@router.post("/chat")
def chat(req: ChatRequest):
    """多轮对话：对话历史中的规则会影响识别结果"""
    try:
        result = _run_chat(req)
        result.pop("file_meta", None)
        return result
    except Exception as e:
        raise HTTPException(500, friendly_llm_error(e))


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def gen():
        try:
            async for event, payload in _aiter_chat_events(req):
                if event == "ping":
                    yield ": keepalive\n\n"
                    continue
                yield _sse(event, payload)
                if event == "step":
                    await asyncio.sleep(0.15)
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
