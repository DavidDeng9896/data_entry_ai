"""把新建表时的 Skill 草稿与已有 Skill 按章节智能合并。"""
from .. import database as db
from .ai_service import _client, _complete, friendly_llm_error

MERGE_PROMPT = """你是科研导入 Skill 编辑器。用户有一份「已有 Skill」和一份「新建草稿」。
请按章节智能合并成一份完整 Markdown Skill，保留两边有用的规则，去重冲突时以草稿为准（草稿通常对应最新列定义）。

必须保留这些章节（可为空，但标题要在）：
# 标题
## 匹配线索
## 目标结果表
## 读取范围
## 主源
## 实体与过滤
## 字段映射
## 不映射
## 特殊值

输出：只返回合并后的完整 Markdown，不要解释，不要用代码围栏。
"""


def mock_merge_skill_markdown(base_md: str, draft_md: str, name: str = "") -> str:
    """Mock：简单拼接两边关键段落，便于无 key 时跑通。"""
    title = name.strip() or "合并 Skill"
    sections = [
        "匹配线索", "目标结果表", "读取范围", "主源",
        "实体与过滤", "字段映射", "不映射", "特殊值",
    ]

    def _section_body(md: str, heading: str) -> str:
        marker = f"## {heading}"
        if marker not in (md or ""):
            return ""
        rest = md.split(marker, 1)[1]
        nxt = rest.find("\n## ")
        body = rest if nxt < 0 else rest[:nxt]
        return body.strip()

    parts = [f"# {title}\n"]
    for h in sections:
        a = _section_body(base_md, h)
        b = _section_body(draft_md, h)
        merged = []
        if a:
            merged.append(a)
        if b and b not in a:
            merged.append(b)
        parts.append(f"## {h}\n" + ("\n\n".join(merged) if merged else "（待补充）") + "\n")
    return "\n".join(parts).strip() + "\n"


def merge_skill_markdown(
    base_md: str,
    draft_md: str,
    *,
    name: str = "",
    force_mock: bool | None = None,
    on_progress=None,
) -> str:
    settings = db.load_model_settings()
    use_mock = settings.get("mock") if force_mock is None else force_mock
    if use_mock:
        return mock_merge_skill_markdown(base_md, draft_md, name=name)
    cfg = settings["text_model"]
    client = _client(cfg)
    msgs = [
        {"role": "system", "content": MERGE_PROMPT},
        {
            "role": "user",
            "content": (
                f"合并后标题建议：{name or '（保持合理标题）'}\n\n"
                f"## 已有 Skill\n{base_md or '（空）'}\n\n"
                f"## 新建草稿\n{draft_md or '（空）'}"
            ),
        },
    ]
    if on_progress:
        on_progress("正在合并 Skill…")
    try:
        raw = _complete(client, cfg["model"], msgs, on_progress=on_progress)
    except Exception as e:
        raise ValueError(friendly_llm_error(e)) from e
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    if not text:
        raise ValueError("模型未返回合并结果")
    return text
