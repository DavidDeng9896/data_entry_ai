"""全局配置与持久化：设置存到 data/settings.json，skill 存到 data/skills/*.md"""
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SKILLS_DIR = DATA_DIR / "skills"
SETTINGS_FILE = DATA_DIR / "settings.json"
COLUMNS_FILE = DATA_DIR / "columns.json"

DATA_DIR.mkdir(exist_ok=True)
SKILLS_DIR.mkdir(exist_ok=True)

# 预置 Binding Assay 结果表表头（迁移到 SQLite 的初始数据）
DEFAULT_COLUMNS = {
    "result": [
        {"field": "cell_line", "title": "Cell Line", "type": "select", "required": True,
         "options": ["CHO01", "CHO02", "CHO03", "CHO04", "CHO05", "CHO06"], "description": "细胞系编号"},
        {"field": "antibody", "title": "Andibody", "type": "text", "required": False, "options": [], "description": "抗体编号"},
        {"field": "cell_type", "title": "Cell Type", "type": "text", "required": False, "options": [], "description": "细胞类型"},
        {"field": "condition", "title": "Condition", "type": "select", "required": False,
         "options": ["Experimental", "Control"], "description": "实验条件"},
        {"field": "concentration", "title": "Concetration (ug/ml)", "type": "number", "required": False, "options": [], "description": "浓度"},
        {"field": "response", "title": "Response (RU)", "type": "number", "required": False, "options": [], "description": "响应值"},
        {"field": "inhibition", "title": "抑制常数", "type": "number", "required": False, "options": [], "description": "抑制常数"},
        {"field": "remark", "title": "备注", "type": "text", "required": False, "options": [], "description": "备注"},
    ],
}

DEFAULT_SETTINGS = {
    "text_model": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
    },
    "vision_model": {
        "base_url": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o",
    },
    "mock": True,  # 没有真实 key 时返回 mock 识别结果，便于先跑通交互
    "parse_max_chars": 0,  # 0 = 解析文件时不截断
}


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = {**DEFAULT_SETTINGS, **data}
            merged["text_model"] = {**DEFAULT_SETTINGS["text_model"], **data.get("text_model", {})}
            merged["vision_model"] = {**DEFAULT_SETTINGS["vision_model"], **data.get("vision_model", {})}
            return merged
        except Exception:
            return dict(DEFAULT_SETTINGS)
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
