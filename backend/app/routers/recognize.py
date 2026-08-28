"""AI 识别接口：上传文件 → 识别填入表格"""
import asyncio
import json

from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.responses import StreamingResponse

from .. import database as db
from ..schemas import RecognizeRequest, ChatRequest
from ..services import file_parser, ai_service
from ..services.intent import classify_intent
from ..services.skill_matcher import resolve_skill

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


def _load_files_content(file_ids: list[str]) -> tuple[str | None, dict]:
    meta = {"count": len(file_ids), "chars": 0, "truncated": False}
    if not file_ids:
        return None, meta
    max_chars = _parse_max_chars()
    chunks: list[str] = []
    total = 0
    truncated = False
    for fid in file_ids:
        try:
            if file_parser.is_image(fid):
                chunk = f"### {fid}\n（已上传图片，当前以文本模式处理）"
                chunks.append(chunk)
                total += len(chunk)
                continue
            text = file_parser.parse_to_text(fid, max_chars=max_chars)
            if "已截断" in text:
                truncated = True
            if text.strip():
                chunk = f"### {fid}\n{text}"
                chunks.append(chunk)
                total += len(text)
        except FileNotFoundError as e:
            raise HTTPException(404, str(e)) from e
    meta["chars"] = total
    meta["truncated"] = truncated
    return ("\n\n---\n\n".join(chunks) if chunks else None), meta


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
    file_content, file_meta = _load_files_content(file_ids)
    last = _last_user_text(req.messages)
    intent = classify_intent(last, has_files=bool(file_ids))

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
    else:
        resolved = _resolve_for_request(req, file_content, allow_auto=True)

    reply, rows = ai_service.chat(
        req.messages,
        req.columns,
        resolved.get("skill_content"),
        file_content,
        intent=intent,
        file_meta=file_meta,
    )
    return {
        "reply": reply,
        "rows": rows,
        "intent": intent,
        "file_meta": file_meta,
        **_skill_meta_payload(resolved),
    }


def _iter_chat_events(req: ChatRequest):
    file_ids = _resolve_file_ids(req)
    last = _last_user_text(req.messages)
    intent = classify_intent(last, has_files=bool(file_ids))

    if intent == "chat":
        yield "step", {"text": "正在理解你的问题…", "intent": intent}
        result = _run_chat(req)
        yield "done", {k: result[k] for k in ("reply", "rows", "intent", "skill_id", "skill_name", "skill_auto", "skill_reason")}
        return

    file_content, file_meta = _load_files_content(file_ids)
    resolved = _resolve_for_request(req, file_content, allow_auto=True)
    if resolved.get("skill_name"):
        yield "step", {"text": f"已加载 Skill：{resolved['skill_name']}", "intent": intent}
    else:
        yield "step", {"text": "未指定模板，仅用基线", "intent": intent}

    n_files = file_meta.get("count") or 0
    chars = file_meta.get("chars") or 0
    if file_meta.get("truncated"):
        yield "step", {"text": f"解析 {n_files} 个附件（共 {chars} 字符，已截断）"}
    else:
        yield "step", {"text": f"解析 {n_files} 个附件（共 {chars} 字符，完整读取）"}

    yield "step", {"text": f"映射 {len(req.columns)} 列"}

    reply, rows = ai_service.chat(
        req.messages,
        req.columns,
        resolved.get("skill_content"),
        file_content,
        intent=intent,
        file_meta=file_meta,
    )
    yield "step", {"text": f"完成 {len(rows)} 行"}
    yield "done", {
        "reply": reply,
        "rows": rows,
        "intent": intent,
        **_skill_meta_payload(resolved),
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
            rows, message = ai_service.recognize_text(file_content, req.columns, resolved.get("skill_content"))
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
        raise HTTPException(500, f"对话失败：{str(e)[:300]}")


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def gen():
        try:
            for event, payload in _iter_chat_events(req):
                yield _sse(event, payload)
                await asyncio.sleep(0.35 if event == "step" else 0)
        except Exception as e:
            yield _sse("error", {"message": f"对话失败：{str(e)[:300]}"})

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
