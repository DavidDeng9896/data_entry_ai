"""设置接口：模型 API 配置（SQLite）+ 连接测试"""
from fastapi import APIRouter
from openai import OpenAI

from .. import database as db
from ..schemas import Settings, ModelConfig
from ..services.ai_service import extra_body_for_model, friendly_llm_error

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
    if not (cfg.model or "").strip():
        return {"ok": False, "message": "模型名为空"}
    try:
        client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key, timeout=20)
        listed: list[str] = []
        try:
            listed = [m.id for m in client.models.list().data][:30]
        except Exception:
            listed = []
        extra = extra_body_for_model(cfg.model)
        kwargs = {"extra_body": extra} if extra else {}
        client.chat.completions.create(
            model=cfg.model.strip(),
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=8,
            **kwargs,
        )
        hint = f"；该地址可见模型：{', '.join(listed[:8])}" if listed else ""
        return {"ok": True, "message": f"模型 {cfg.model} 调用成功（{cfg.base_url}）{hint}", "models": listed}
    except Exception as e:
        return {"ok": False, "message": friendly_llm_error(e)}
