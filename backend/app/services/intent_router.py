"""会话意图：AI/启发式判定 extract|answer|edit|clarify，并合并会话规则。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .table_edit import looks_like_local_edit

_CLEAR_MARKERS = ("忘掉", "忘记刚才", "清空规则", "按默认", "不要之前的规则", "重置规则")
_ANSWER_HINTS = (
    "为啥", "为什么", "为何", "是不是", "对吗", "解释", "怎么来的",
    "没匹配", "没有匹配", "先别识别", "先别抽",
)
_EXTRACT_HINTS = (
    "识别", "导入", "提取", "填表", "重新识别", "覆盖", "再导", "再抽", "重新抽",
    "过滤", "只要", "按规则", "分析", "解析", "读附件", "看附件", "抽数", "开始识别",
)


@dataclass
class IntentDecision:
    action: str  # extract | answer | edit | clarify
    rule_delta: str = ""
    clear_rules: bool = False
    reason: str = ""
    reply: str = ""  # clarify 时直接给用户的问题


def api_intent(action: str) -> str:
    if action == "extract":
        return "recognize"
    if action == "edit":
        return "edit"
    return "chat"


def merge_session_rules(current: str, delta: str = "", *, clear: bool = False) -> str:
    if clear:
        return ""
    cur = (current or "").strip()
    add = (delta or "").strip()
    if not add:
        return cur
    if not cur:
        return add
    if add in cur:
        return cur
    return f"{cur}\n{add}"


def _wants_clear(text: str) -> bool:
    return any(m in text for m in _CLEAR_MARKERS)


def _rule_delta_from_text(text: str, action: str) -> str:
    t = (text or "").strip()
    if not t or _wants_clear(t):
        return ""
    # 纯催促、无约束的短句不记规则
    if action == "extract" and re.fullmatch(r"(开始|识别|导入|请识别|请导入|抽数)?[!！。.~…]*", t):
        return ""
    if action in ("extract", "answer", "edit", "clarify"):
        # 有实质约束才记；过短的「开始」已排除
        if len(t) < 4 and action != "extract":
            return ""
        return t
    return ""


def _mock_decide(
    text: str,
    *,
    has_files: bool,
    has_rows: bool,
) -> IntentDecision:
    t = (text or "").strip()
    if not t:
        if has_files:
            return IntentDecision("extract", reason="空发送+有附件")
        return IntentDecision("answer", reason="无附件无内容")

    clear = _wants_clear(t)
    if any(h in t for h in _ANSWER_HINTS) or re.search(r"[吗呢？?]", t):
        return IntentDecision(
            "answer",
            rule_delta="" if clear else _rule_delta_from_text(t, "answer"),
            clear_rules=clear,
            reason="问答线索",
        )

    if looks_like_local_edit(t):
        if has_rows:
            return IntentDecision(
                "edit",
                rule_delta=_rule_delta_from_text(t, "edit"),
                clear_rules=clear,
                reason="本地改格子",
            )
        if has_files:
            return IntentDecision(
                "extract",
                rule_delta=_rule_delta_from_text(t, "extract"),
                clear_rules=clear,
                reason="表空，改格子要求改为抽数",
            )
        return IntentDecision(
            "clarify",
            clear_rules=clear,
            reason="要改格子但表空且无附件",
            reply="当前结果表还是空的，也没有附件。请先上传报告，或说明你想怎么改。",
        )

    if any(h in t for h in _EXTRACT_HINTS):
        return IntentDecision(
            "extract",
            rule_delta=_rule_delta_from_text(t, "extract"),
            clear_rules=clear,
            reason="抽数线索",
        )

    if has_files and not has_rows:
        return IntentDecision(
            "extract",
            rule_delta=_rule_delta_from_text(t, "extract"),
            clear_rules=clear,
            reason="有附件且表空，默认识别",
        )

    if has_rows and not has_files:
        return IntentDecision(
            "answer",
            rule_delta=_rule_delta_from_text(t, "answer"),
            clear_rules=clear,
            reason="已有表无新附件，默认问答",
        )

    if has_rows and has_files:
        return IntentDecision(
            "clarify",
            rule_delta=_rule_delta_from_text(t, "clarify"),
            clear_rules=clear,
            reason="有表又有附件，意图不清",
            reply="你是想按这句话的新要求重新抽附件覆盖当前表，还是只回答问题、不动表？",
        )

    return IntentDecision("answer", reason="默认问答")


_DECIDE_SYSTEM = """你是数据导入助手的意图分类器。只输出一个 JSON 对象，不要 markdown。
字段：
- action: extract | answer | edit | clarify
- rule_delta: 本句要记入会话的导入约束（无则 ""）
- clear_rules: true/false，用户是否要求忘掉/清空会话规则
- reason: 短中文原因
- reply: 仅 clarify 时给用户的一句确认问话，其它 action 必须 ""

规则：
- extract：要读附件抽数/重导/按新规则覆盖预览表
- answer：只解释或讨论已填表，不抽数
- edit：只改已填格子（如改小数位），不重读附件
- clarify：拿不准时问用户，不要替用户做死决定
- 表空且有附件、用户催分析/开始：倾向 extract，禁止假装没附件
- 空发送由调用方处理，你不会看到空文本
"""


def _llm_decide(
    text: str,
    *,
    has_files: bool,
    has_rows: bool,
    session_rules: str,
    file_names: list[str],
    sample_ids: list[str],
    llm_cfg: dict,
) -> IntentDecision:
    from openai import OpenAI

    from .ai_service import strip_model_noise

    client = OpenAI(
        base_url=llm_cfg.get("base_url") or None,
        api_key=llm_cfg.get("api_key") or "sk-empty",
        timeout=30.0,
        max_retries=0,
    )
    user = {
        "user_text": text,
        "has_files": has_files,
        "file_names": (file_names or [])[:12],
        "has_rows": has_rows,
        "sample_cpds_ids": (sample_ids or [])[:8],
        "session_rules": (session_rules or "")[:2000],
    }
    resp = client.chat.completions.create(
        model=llm_cfg.get("model") or "",
        messages=[
            {"role": "system", "content": _DECIDE_SYSTEM},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        temperature=0,
    )
    raw = strip_model_noise((resp.choices[0].message.content or "").strip())
    m = re.search(r"\{[\s\S]*\}", raw)
    data = json.loads(m.group(0) if m else raw)
    action = str(data.get("action") or "clarify").strip().lower()
    if action not in ("extract", "answer", "edit", "clarify"):
        action = "clarify"
    reply = str(data.get("reply") or "").strip()
    if action == "clarify" and not reply:
        reply = "你是想重新抽附件覆盖当前表，只改已填格子，还是只回答问题？"
    return IntentDecision(
        action=action,
        rule_delta=str(data.get("rule_delta") or "").strip(),
        clear_rules=bool(data.get("clear_rules")),
        reason=str(data.get("reason") or "")[:200],
        reply=reply,
    )


def decide_action(
    text: str,
    *,
    has_files: bool = False,
    has_rows: bool = False,
    session_rules: str = "",
    file_names: list[str] | None = None,
    sample_ids: list[str] | None = None,
    use_llm: bool = False,
    llm_cfg: dict | None = None,
) -> IntentDecision:
    """返回本轮动作。空发送+有附件由调用方可直接钉 extract；此处仍兼容。"""
    t = (text or "").strip()
    if not t and has_files:
        return IntentDecision("extract", reason="空发送+有附件")
    if use_llm and llm_cfg and (llm_cfg.get("api_key") or "").strip() and t:
        try:
            return _llm_decide(
                t,
                has_files=has_files,
                has_rows=has_rows,
                session_rules=session_rules,
                file_names=file_names or [],
                sample_ids=sample_ids or [],
                llm_cfg=llm_cfg,
            )
        except Exception:
            # 降级到启发式
            pass
    return _mock_decide(t, has_files=has_files, has_rows=has_rows)
