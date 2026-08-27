"""Pydantic 模型：接口请求/响应"""
from typing import Optional
from pydantic import BaseModel


class ModelConfig(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = ""


class Settings(BaseModel):
    text_model: ModelConfig
    vision_model: ModelConfig
    mock: bool = True


class ColumnDef(BaseModel):
    """表头列定义：与前端表头设置一致"""
    field: str                       # 列字段名（英文标识）
    title: str                       # 列显示名
    type: str = "text"               # text | number | date | select
    required: bool = False
    options: list[str] = []          # select 类型的候选值
    description: str = ""            # 列说明，帮助 AI 理解语义


class SkillMeta(BaseModel):
    name: str
    filename: str
    enabled: bool = False
    description: str = ""


class SkillContent(BaseModel):
    filename: str
    content: str


class RecognizeRequest(BaseModel):
    file_id: str                     # 上传后返回的文件 id
    columns: list[ColumnDef]         # 当前表头
    skill_id: Optional[int] = None   # 可选 skill 模板 id


class RecognizeResponse(BaseModel):
    rows: list[dict]                 # [{field: value, ...}, ...]
    message: str = ""


class ChatMessage(BaseModel):
    role: str                        # user | assistant
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]      # 完整对话历史（多轮）
    columns: list[ColumnDef]         # 当前表头
    skill_id: Optional[int] = None   # 可选 skill 模板 id
    file_id: Optional[str] = None    # 已上传的文件 id（识别上下文）


class ChatResponse(BaseModel):
    reply: str                       # 助手对话回复（纯文本）
    rows: list[dict] = []            # 本轮若产生识别结果，返回结构化行数据
