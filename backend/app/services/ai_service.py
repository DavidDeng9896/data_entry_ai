"""AI 识别：把解析后的文件内容 + 表头定义 + 可选 skill 规则 → OpenAI 兼容接口 → 结构化行数据。
支持文本模型（Excel/CSV/PDF）和视觉模型（图片扫描件）。mock 模式返回演示数据。
"""
import base64
import json
import re

from openai import OpenAI

from .. import database as db
from ..schemas import ColumnDef, ChatMessage
from . import file_parser


def _columns_prompt(columns: list[ColumnDef]) -> str:
    lines = []
    for c in columns:
        desc = f"- 字段 `{c.field}`（{c.title}），类型 {c.type}"
        if c.required:
            desc += "，必填"
        if c.type == "select" and c.options:
            desc += f"，可选值：{'、'.join(c.options)}"
        if c.description:
            desc += f"，说明：{c.description}"
        lines.append(desc)
    return "\n".join(lines)


def _build_system_prompt(columns: list[ColumnDef], skill_content: str | None) -> str:
    prompt = f"""你是科研数据录入助手。用户会给你一份从 CRO 报告/仪器输出/历史文档中解析出的原始内容，你要把其中的数据提取并映射到目标表格的列。

目标表格的列定义如下：
{_columns_prompt(columns)}

要求：
1. 只输出 JSON 数组，每个元素是一行数据的对象，key 用字段名，value 用字符串。
2. 只填充上面定义的列，源数据中多余的列丢弃，缺失的填空字符串 ""。
3. select 类型的列，值必须尽量匹配到候选值之一；数字列只保留数值；日期统一 YYYY-MM-DD。
4. 不要编造数据，源内容里没有的就留空。
5. 不要输出任何解释、markdown 代码块标记，只输出纯 JSON 数组。"""
    if skill_content:
        prompt += f"\n\n以下是用户选择的导入模板规则，请优先遵循：\n{skill_content}"
    return prompt


def _extract_json_array(text: str) -> list[dict]:
    """从模型输出中提取 JSON 数组，容忍 ```json 包裹和前后杂文本"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [dict(item) for item in data if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass
    return []


def _mock_rows(columns: list[ColumnDef]) -> list[dict]:
    """mock 模式：按列类型生成演示数据，模拟 Binding Assay 场景"""
    samples = {
        "text": ["CHO01", "CHO02", "CHO03", "CHO04", "CHO05", "CHO06"],
        "number": ["0.02", "0.04", "0.12", "1.02", "0.32", "0.56"],
        "date": ["2026-08-01", "2026-08-03", "2026-08-05", "2026-08-08", "2026-08-10", "2026-08-12"],
    }
    rows = []
    for i in range(6):
        row = {}
        for c in columns:
            if c.type == "select" and c.options:
                row[c.field] = c.options[i % len(c.options)]
            elif c.type in samples:
                row[c.field] = samples[c.type][i % len(samples[c.type])]
            else:
                row[c.field] = f"{c.title}{i+1}"
        rows.append(row)
    return rows


def _client(cfg: dict) -> OpenAI:
    return OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"] or "sk-empty")


def recognize_text(content: str, columns: list[ColumnDef], skill_content: str | None) -> tuple[list[dict], str]:
    settings = db.load_model_settings()
    if settings["mock"]:
        return _mock_rows(columns), "mock 模式返回演示数据（在设置中关闭 mock 并配置 API key 后走真实模型）"

    cfg = settings["text_model"]
    client = _client(cfg)
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": _build_system_prompt(columns, skill_content)},
            {"role": "user", "content": f"请从以下内容中提取数据：\n\n{content}"},
        ],
        temperature=0,
    )
    rows = _extract_json_array(resp.choices[0].message.content or "")
    return rows, "" if rows else "模型未返回有效数据，请检查内容或模型配置"


_CHAT_SYSTEM = """你是数据录入助手，帮助用户把 CRO 报告、仪器输出等原始文件中的数据导入目标表格。

当前目标表格的列定义：
{columns}

{skill_section}
交互规则：
1. 用户在对话中会提出对本次导入的额外要求或规则（如单位换算、列映射、过滤某些行、默认值等），你必须记住并遵循对话中出现过的所有规则。
2. 当用户上传了文件（下方会附上解析出的原始内容）且要求识别时，把数据映射到目标列。
3. 识别结果输出格式：先简短说明（1-2 句，告知识别了多少行、应用了哪些规则），然后单独一行输出：
<<<ROWS>>>
[JSON 数组，每个元素一行数据，key 用字段名]
4. 没有文件或用户只是聊天/补充规则时，正常对话确认即可，不要输出 <<<ROWS>>> 块。
5. 不要编造数据，源内容里没有的留空。"""


def chat(messages: list[ChatMessage], columns: list[ColumnDef], skill_content: str | None,
         file_content: str | None) -> tuple[str, list[dict]]:
    """多轮对话：对话历史 + 可选文件内容 -> (回复文本, 结构化行数据或空)"""
    settings = db.load_model_settings()

    system = _CHAT_SYSTEM.format(
        columns=_columns_prompt(columns),
        skill_section=f"用户已选择的导入模板规则，请优先遵循：\n{skill_content}" if skill_content else "",
    )

    msgs: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        msgs.append({"role": m.role, "content": m.content})

    if file_content:
        msgs.append({"role": "user", "content": f"[已上传文件的解析内容]\n{file_content}"})

    if settings["mock"]:
        return _mock_chat_reply(messages, columns, file_content)

    cfg = settings["text_model"]
    client = _client(cfg)
    resp = client.chat.completions.create(model=cfg["model"], messages=msgs, temperature=0)
    raw = resp.choices[0].message.content or ""
    return _split_chat_reply(raw, columns)


def _mock_chat_reply(messages: list[ChatMessage], columns: list[ColumnDef], file_content: str | None) -> tuple[str, list[dict]]:
    """mock 模式：模拟对话交互，规则随对话累积生效"""
    rules = [m.content for m in messages if m.role == "user" and m.content.strip()]
    last = rules[-1] if rules else ""
    # 用户本轮要求识别：有文件就返回数据行
    wants_recognize = any(kw in last for kw in ("识别", "导入", "提取", "解析", "填入")) or "帮我" in last
    if file_content and wants_recognize:
        rows = _mock_rows(columns)
        rule_note = f"，已应用你在对话中提出的 {len(rules)} 条规则" if rules else ""
        reply = f"已识别出 {len(rows)} 行数据{rule_note}（mock 模式，返回演示数据）。已填入表格，可在对话中继续补充规则后重新识别。"
        return reply, rows
    if file_content:
        rows = _mock_rows(columns)
        reply = f"文件已收到（mock 模式）。需要我现在识别导入吗？也可以继续补充规则。说「识别导入」我就返回 {len(rows)} 行演示数据。"
        return reply, []
    reply = f"收到：{last or '（空）'}。我会把它作为导入规则记住（mock 模式）。你可以继续补充规则，或上传文件后让我识别。"
    return reply, []


def _split_chat_reply(raw: str, columns: list[ColumnDef]) -> tuple[str, list[dict]]:
    """把模型回复拆成：对话文本 + <<<ROWS>>> 后的 JSON 行数据"""
    if "<<<ROWS>>>" in raw:
        text, _, rows_part = raw.partition("<<<ROWS>>>")
        rows = _extract_json_array(rows_part)
        return text.strip(), rows
    return raw.strip(), []


def recognize_image(file_id: str, columns: list[ColumnDef], skill_content: str | None) -> tuple[list[dict], str]:
    settings = db.load_model_settings()
    if settings["mock"]:
        return _mock_rows(columns), "mock 模式返回演示数据（图片识别，关闭 mock 并配置视觉模型后生效）"

    cfg = settings["vision_model"]
    img_bytes, ext = file_parser.get_image_bytes(file_id)
    b64 = base64.b64encode(img_bytes).decode()
    mime = "jpeg" if ext in {"jpg", "jpeg"} else ext
    client = _client(cfg)
    resp = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": _build_system_prompt(columns, skill_content)},
            {"role": "user", "content": [
                {"type": "text", "text": "请识别这张图片中的表格数据并映射到目标列："},
                {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
            ]},
        ],
        temperature=0,
    )
    rows = _extract_json_array(resp.choices[0].message.content or "")
    return rows, "" if rows else "视觉模型未返回有效数据，请检查图片清晰度或模型配置"
