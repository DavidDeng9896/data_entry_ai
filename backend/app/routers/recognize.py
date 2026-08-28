"""AI 识别接口：上传文件 → 识别填入表格"""
from fastapi import APIRouter, UploadFile, HTTPException

from .. import database as db
from ..schemas import RecognizeRequest, ChatRequest
from ..services import file_parser, ai_service

router = APIRouter(prefix="/api/recognize", tags=["recognize"])


def _resolve_file_ids(req: ChatRequest) -> list[str]:
    ids: list[str] = []
    if req.file_id:
        ids.append(req.file_id)
    for fid in req.file_ids or []:
        if fid and fid not in ids:
            ids.append(fid)
    return ids


def _load_files_content(file_ids: list[str]) -> str | None:
    if not file_ids:
        return None
    chunks: list[str] = []
    for fid in file_ids:
        try:
            if file_parser.is_image(fid):
                chunks.append(f"### {fid}\n（已上传图片，当前以文本模式处理）")
                continue
            text = file_parser.parse_to_text(fid)
            if text.strip():
                chunks.append(f"### {fid}\n{text}")
        except FileNotFoundError as e:
            raise HTTPException(404, str(e)) from e
    return "\n\n---\n\n".join(chunks) if chunks else None


@router.post("/upload")
async def upload(file: UploadFile):
    content = await file.read()
    if not content:
        raise HTTPException(400, "文件为空")
    info = file_parser.save_upload(file.filename or "unnamed", content)
    return {"file_id": info["file_id"], "filename": info["filename"], "ext": info["ext"]}


@router.post("/run")
def run(req: RecognizeRequest):
    # 读取可选 skill 模板内容（skill_id 从 SQLite 取）
    skill_content = None
    if req.skill_id:
        content = db.get_skill_content(req.skill_id)
        if content:
            skill_content = content

    try:
        if file_parser.is_image(req.file_id):
            rows, message = ai_service.recognize_image(req.file_id, req.columns, skill_content)
        else:
            content = file_parser.parse_to_text(req.file_id)
            if not content.strip():
                return {"rows": [], "message": "未能从文件中解析出内容"}
            rows, message = ai_service.recognize_text(content, req.columns, skill_content)
        return {"rows": rows, "message": message}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"识别失败：{str(e)[:300]}")


@router.post("/chat")
def chat(req: ChatRequest):
    """多轮对话：对话历史中的规则会影响识别结果"""
    skill_content = None
    if req.skill_id:
        content = db.get_skill_content(req.skill_id)
        if content:
            skill_content = content

    file_content = _load_files_content(_resolve_file_ids(req))

    try:
        reply, rows = ai_service.chat(req.messages, req.columns, skill_content, file_content)
        return {"reply": reply, "rows": rows}
    except Exception as e:
        raise HTTPException(500, f"对话失败：{str(e)[:300]}")
