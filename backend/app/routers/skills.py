"""Skill 管理：SQLite 存储 + .md 导入导出。
- 列表/详情/新建/编辑/删除/启用
- POST /import-md：上传 .md 文件导入为新 skill
- GET /{id}/export-md：下载 skill 为 .md 文件
"""
import re

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from .. import database as db

router = APIRouter(prefix="/api/skills", tags=["skills"])


class SkillSave(BaseModel):
    id: int | None = None
    name: str
    content: str = ""


class SkillEnable(BaseModel):
    id: int | None = None


@router.get("")
def list_skills():
    return db.list_skills()


@router.get("/{skill_id}")
def get_skill(skill_id: int):
    skill = db.get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "skill 不存在")
    return skill


@router.post("")
def save_skill(body: SkillSave):
    if not body.name.strip():
        raise HTTPException(400, "名称不能为空")
    skill_id = db.save_skill(body.id, body.name.strip(), body.content)
    return {"ok": True, "id": skill_id}


@router.delete("/{skill_id}")
def delete_skill(skill_id: int):
    db.delete_skill(skill_id)
    return {"ok": True}


@router.post("/enable")
def enable_skill(body: SkillEnable):
    db.set_enabled_skill(body.id)
    return {"ok": True}


@router.post("/import-md")
async def import_md(file: UploadFile):
    """上传 .md 文件导入为新 skill，文件名（去扩展名）作为名称"""
    content = (await file.read()).decode("utf-8", errors="replace")
    if not content.strip():
        raise HTTPException(400, "文件内容为空")
    name = re.sub(r"\.md$", "", file.filename or "未命名")
    # 内容首行 # 标题优先
    for line in content.splitlines():
        if line.startswith("# "):
            name = line[2:].strip()
            break
    skill_id = db.save_skill(None, name, content)
    return {"ok": True, "id": skill_id, "name": name}


@router.get("/{skill_id}/export-md")
def export_md(skill_id: int):
    skill = db.get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "skill 不存在")
    from urllib.parse import quote
    filename = quote(f"{skill['name']}.md")
    return Response(
        content=skill["content"],
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )
