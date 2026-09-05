"""章节意图：先标题启发式，拿不准再模型；对不上则列目录请用户指认。"""
from __future__ import annotations

import json
import re

from .section_model import Section, catalog_lines, render_sections
from .sheet_focus import _SELF_KEEP, _SELF_SKIP, _looks_like_filename, parse_sheet_policy, _listed


def heuristic_role(title: str) -> str:
    t = title or ""
    if _looks_like_filename(t):
        return "unknown"
    if _SELF_SKIP.search(t):
        return "process"
    if _SELF_KEEP.search(t):
        return "result"
    return "unknown"


def apply_heuristic(sections: list[Section]) -> list[Section]:
    out = []
    for sec in sections:
        role = "unknown" if sec.kind == "file" else heuristic_role(sec.title)
        out.append(Section(sec.title, sec.kind, sec.text, sec.images, role))
    return out


def apply_skill_policy(sections: list[Section], skill_content: str | None) -> list[Section] | None:
    policy = parse_sheet_policy(skill_content)
    if not policy:
        return None
    include = policy.get("include") or []
    skip = policy.get("skip") or []
    out = []
    for sec in sections:
        if sec.kind == "file":
            out.append(sec)
            continue
        if skip and _listed(sec.title, skip):
            out.append(Section(sec.title, sec.kind, sec.text, sec.images, "process"))
        elif include and _listed(sec.title, include):
            out.append(Section(sec.title, sec.kind, sec.text, sec.images, "result"))
        elif include:
            out.append(Section(sec.title, sec.kind, sec.text, sec.images, "process"))
        else:
            out.append(sec)
    return out


def _llm_label_unknown(sections: list[Section], table_name: str, llm_cfg: dict) -> list[Section]:
    unknown = [s for s in sections if s.kind != "file" and s.role == "unknown"]
    if not unknown:
        return sections
    from openai import OpenAI
    from .ai_service import strip_model_noise

    client = OpenAI(
        base_url=llm_cfg.get("base_url") or None,
        api_key=llm_cfg.get("api_key") or "sk-empty",
        timeout=30.0,
        max_retries=0,
    )
    payload = {
        "table": table_name,
        "sections": [{"title": s.title, "kind": s.kind, "head": (s.text or "")[:240]} for s in unknown],
    }
    resp = client.chat.completions.create(
        model=llm_cfg.get("model") or "",
        messages=[
            {
                "role": "system",
                "content": (
                    "判断每个章节像不像当前结果表的主数据。只输出 JSON 数组："
                    '[{"title":"...","role":"result|process|unknown"}]'
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0,
    )
    raw = strip_model_noise(resp.choices[0].message.content or "")
    m = re.search(r"\[[\s\S]*\]", raw)
    rows = json.loads(m.group(0) if m else raw)
    by_title = {str(r.get("title") or ""): str(r.get("role") or "unknown") for r in rows}
    out = []
    for sec in sections:
        role = by_title.get(sec.title, sec.role)
        if role not in ("result", "process", "unknown"):
            role = sec.role
        out.append(Section(sec.title, sec.kind, sec.text, sec.images, role))
    return out


def classify_sections(
    sections: list[Section],
    *,
    skill_content: str | None = None,
    table_name: str = "",
    use_llm: bool = False,
    llm_cfg: dict | None = None,
) -> list[Section]:
    tagged = apply_skill_policy(sections, skill_content)
    if tagged is None:
        tagged = apply_heuristic(sections)
    if use_llm and llm_cfg and (llm_cfg.get("api_key") or "").strip():
        try:
            tagged = _llm_label_unknown(tagged, table_name, llm_cfg)
        except Exception:
            pass
    return tagged


def result_sections(sections: list[Section]) -> list[Section]:
    return [s for s in sections if s.kind != "file" and s.role == "result"]


def pick_sections_by_user(text: str, sections: list[Section]) -> list[Section]:
    """用户说「看 Result sheet / 看第 3 页」时只留点名的章。"""
    t = (text or "").strip()
    if not t:
        return []
    picked = []
    for sec in sections:
        if sec.kind == "file":
            continue
        title = sec.title
        if title and title in t:
            picked.append(sec)
            continue
        if sec.kind == "page" and re.search(rf"第\s*{re.escape(str(title))}\s*页", t):
            picked.append(sec)
    return picked


def guess_result_title(sections: list[Section]) -> str:
    results = result_sections(sections)
    if results:
        return results[0].title
    for sec in sections:
        if sec.kind != "file" and (sec.text or "").strip():
            return sec.title
    return ""


def ask_user_where(sections: list[Section]) -> str:
    lines = catalog_lines(sections)
    guess = guess_result_title(sections)
    hint = f"我猜结果更可能在「{guess}」。" if guess else "我还不能确定结果在哪一节。"
    catalog = "\n".join(lines) if lines else "（没有切出可用章节）"
    return (
        f"按章节看过一遍，没有找到和当前结果表明显对应的数据块。{hint}\n\n"
        f"解析到的部分：\n{catalog}\n\n"
        "请告诉我看哪一节，例如「看 Result sheet」或「看第 3 页」。"
    )


def content_for_extract(
    sections: list[Section],
    *,
    skill_content: str | None = None,
    user_text: str = "",
    table_name: str = "",
    use_llm: bool = False,
    llm_cfg: dict | None = None,
) -> tuple[str, list[Section], str, list[Section]]:
    """返回 (正文, 选用章节, 模式 result|picked|full, 全部已标注章节)。"""
    tagged = classify_sections(
        sections, skill_content=skill_content, table_name=table_name,
        use_llm=use_llm, llm_cfg=llm_cfg,
    )
    picked = pick_sections_by_user(user_text, tagged)
    if picked:
        return render_sections(picked), picked, "picked", tagged
    results = result_sections(tagged)
    if results:
        return render_sections(results), results, "result", tagged
    selectable = [s for s in tagged if s.kind != "file"]
    return render_sections(selectable or tagged), selectable or tagged, "full", tagged
