"""设置接口：模型 API 配置（SQLite）+ 连接测试"""
from fastapi import APIRouter
from openai import OpenAI

from .. import database as db
from ..schemas import Settings, ModelConfig

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    return db.load_model_settings()


@router.put("")
def update_settings(settings: Settings):
    db.save_model_settings(settings.model_dump())
    return {"ok": True}


@router.post("/test")
def test_connection(cfg: ModelConfig):
    if not cfg.api_key:
        return {"ok": False, "message": "api_key 为空"}
    try:
        client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key, timeout=15)
        client.models.list()
        return {"ok": True, "message": f"连接成功（{cfg.base_url}）"}
    except Exception as e:
        return {"ok": False, "message": f"连接失败：{str(e)[:200]}"}
