"""AI 识别接口：上传文件 → 识别填入表格"""
from fastapi import APIRouter, UploadFile, HTTPException

from .. import database as db
from ..schemas import RecognizeRequest, ChatRequest
from ..services import file_parser, ai_service

router = APIRouter(prefix="/api/recognize", tags=["recognize"])


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

    file_content = None
    if req.file_id:
        try:
            if file_parser.is_image(req.file_id):
                file_content = "（已上传图片文件，图片识别需在设置中配置视觉模型，当前对话先以文本方式处理）"
            else:
                file_content = file_parser.parse_to_text(req.file_id)
        except FileNotFoundError as e:
            raise HTTPException(404, str(e))

    try:
        reply, rows = ai_service.chat(req.messages, req.columns, skill_content, file_content)
        return {"reply": reply, "rows": rows}
    except Exception as e:
        raise HTTPException(500, f"对话失败：{str(e)[:300]}")
