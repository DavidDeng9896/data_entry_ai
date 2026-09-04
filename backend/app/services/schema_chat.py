"""建表对话：解析附件 + 模型/mock → 列配置与 Skill 草稿。"""
from .. import database as db
from ..schemas import ChatMessage, ColumnDef
from . import file_parser
from .ai_service import _client, _complete, friendly_llm_error  # noqa: F401
from .schema_extract import compose_schema_response, split_schema_reply
from .schema_intent import classify_schema_intent
from .schema_prompt import SCHEMA_SYSTEM_PROMPT

DEMO_COLUMNS = [
    {
        "field": "cpds_id", "title": "Cpds ID", "type": "text", "required": True,
        "options": [], "description": "化合物内部编号",
    },
    {
        "field": "iv_1mpk_cl_l_h_kg", "title": "IV (1 mpk) CL (L/h/kg)", "type": "number",
        "required": False, "options": [], "description": "静脉清除率，源表头常见 Cl_obs",
    },
    {
        "field": "iv_1mpk_vss_l_kg", "title": "IV (1 mpk) Vss (L/kg)", "type": "number",
        "required": False, "options": [], "description": "稳态分布容积",
    },
    {
        "field": "iv_1mpk_auc0_t_h_ng_ml", "title": "IV (1 mpk) AUC0-t (h*ng/mL)", "type": "number",
        "required": False, "options": [], "description": "静脉暴露量 AUClast",
    },
    {
        "field": "iv_1mpk_t1_2_hr", "title": "IV (1 mpk) T1/2 (hr)", "type": "number",
        "required": False, "options": [], "description": "消除半衰期",
    },
    {
        "field": "po_5mpk_pct_f", "title": "PO (5 mpk) %F", "type": "number",
        "required": False, "options": [], "description": "口服生物利用度",
    },
]

DEMO_SKILL_MD = """# PK · mock 演示版式

## 匹配线索
- 用户描述或演示附件

## 目标结果表
Dog PK

## 读取范围
- 读取：封面、PK 参数、结果汇总
- 跳过：原始数据、方法、标曲

## 主源
- 主源：PK 参数（已汇总终点）
- 方法页只用于理解单位，不建列

## 实体与过滤
- 实体：化合物 ID
- 对照行不入库

## 字段映射
| 目标字段 | 源 | 变换 |
| --- | --- | --- |
| `cpds_id` | 化合物 ID | 原样 |
| `iv_1mpk_cl_l_h_kg` | Cl_obs (L/h/kg) | 数值 |
| `iv_1mpk_vss_l_kg` | Vss_obs (L/kg) | 数值 |
| `iv_1mpk_auc0_t_h_ng_ml` | AUClast | 数值 |
| `iv_1mpk_t1_2_hr` | HL_Lambda_z (h) | 数值 |
| `po_5mpk_pct_f` | %F | 数值 |

## 不映射
方法参数、原始时程、试剂、对照

## 特殊值
- NA / N/A → 空
"""


def _last_user(messages: list[ChatMessage]) -> str:
    for m in reversed(messages or []):
        if getattr(m, "role", None) == "user" and (m.content or "").strip():
            return m.content.strip()
    return ""


def _dump_columns(columns) -> list[dict]:
    out = []
    for c in columns or []:
        if isinstance(c, ColumnDef):
            out.append(c.model_dump())
        elif isinstance(c, dict):
            out.append(c)
    return out


def load_schema_files(file_ids: list[str], on_progress=None) -> str:
    if not file_ids:
        return ""
    parts = []
    n = len(file_ids)
    for i, fid in enumerate(file_ids, 1):
        label = file_parser.original_filename(fid)
        if on_progress:
            on_progress(f"正在解析附件 {i}/{n}：{label}")
        if file_parser.is_image(fid):
            parts.append(f"### 文件: {label}\n（已上传图片，请结合文件名与用户说明设计列）")
            continue
        text = file_parser.parse_to_text(fid, max_chars=0)
        parts.append(f"### 文件: {label}\n{text}")
    return "\n\n---\n\n".join(parts)


def mock_schema_reply(last: str, intent: str) -> tuple[str, dict | None]:
    if intent != "schema":
        return (
            f"收到你的问题：{last or '（空）'}。本轮按问答处理，不改列配置（mock 模式）。",
            None,
        )
    parsed = {
        "name": "Dog PK",
        "description": "比格犬 PK 结果表",
        "columns": [dict(c) for c in DEMO_COLUMNS],
        "skill_name": "PK · mock 演示版式",
        "skill_md": DEMO_SKILL_MD,
    }
    reply = (
        "1. 已按内部规范抽列\n"
        "2. 方法/原始页未建列\n"
        "已生成 Dog PK 列配置（mock 模式）。"
    )
    return reply, parsed


def _draft_context(name: str, description: str, columns, skill_name: str, skill_md: str) -> str:
    cols = _dump_columns(columns)
    lines = [f"- {c.get('field')}（{c.get('title')}）{c.get('type')}" for c in cols]
    col_block = "\n".join(lines) if lines else "（空）"
    return (
        f"## 当前草稿\n表名：{name or '（空）'}\n描述：{description or '（空）'}\n"
        f"列：\n{col_block}\nSkill 名：{skill_name or '（空）'}\n"
        f"Skill 正文（可修订）：\n{skill_md or '（空）'}\n"
    )


def _llm_schema(messages, file_content: str, name, description, columns, skill_name, skill_md, on_progress=None) -> tuple[str, dict | None]:
    settings = db.load_model_settings()
    cfg = settings["text_model"]
    client = _client(cfg)
    msgs = [
        {"role": "system", "content": SCHEMA_SYSTEM_PROMPT},
        {"role": "user", "content": _draft_context(name, description, columns, skill_name, skill_md)},
    ]
    for m in messages or []:
        msgs.append({"role": m.role, "content": m.content})
    if file_content:
        msgs.append({"role": "user", "content": f"[以下是全部附件解析，含各 sheet]\n{file_content}"})
    if on_progress:
        on_progress("正在调用模型设计列…")
    raw = _complete(client, cfg["model"], msgs, on_progress=on_progress)
    return split_schema_reply(raw)


def run_schema_chat(
    messages: list[ChatMessage],
    file_ids: list[str] | None = None,
    name: str = "",
    description: str = "",
    columns=None,
    skill_name: str = "",
    skill_md: str = "",
    on_progress=None,
) -> dict:
    file_ids = [f for f in (file_ids or []) if f]
    last = _last_user(messages)
    intent = classify_schema_intent(last, has_files=bool(file_ids))
    file_content = ""
    if intent == "schema" and file_ids:
        file_content = load_schema_files(file_ids, on_progress=on_progress)
    settings = db.load_model_settings()
    if settings.get("mock"):
        reply, parsed = mock_schema_reply(last, intent)
    else:
        try:
            reply, parsed = _llm_schema(
                messages, file_content, name, description, columns, skill_name, skill_md,
                on_progress=on_progress,
            )
        except Exception as e:
            return compose_schema_response(
                "chat",
                friendly_llm_error(e),
                None,
                {
                    "name": name, "description": description, "columns": _dump_columns(columns),
                    "skill_name": skill_name, "skill_md": skill_md,
                },
                last,
            )
    if intent == "chat":
        parsed = None
    return compose_schema_response(
        intent,
        reply,
        parsed,
        {
            "name": name, "description": description, "columns": _dump_columns(columns),
            "skill_name": skill_name, "skill_md": skill_md,
        },
        last,
    )
