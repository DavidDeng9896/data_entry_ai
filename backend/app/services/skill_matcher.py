"""按用户指定或文件内容匹配导入 Skill。匹配不上则只用基线。"""
import json
import re

from openai import OpenAI

from ..schemas import ColumnDef

_STOP = {"sheet", "the", "and", "for", "with", "from", "含", "或", "的", "表", "报告"}


def _clue_text(content: str) -> str:
    m = re.search(r"##\s*匹配线索([\s\S]*?)(?:\n##\s|\Z)", content or "")
    return m.group(1) if m else (content or "")[:1500]


def score_skill(
    skill: dict,
    *,
    table_name: str,
    columns: list[ColumnDef],
    file_content: str,
) -> int:
    blob = f"{skill.get('name') or ''}\n{skill.get('content') or ''}".lower()
    score = 0
    tn = (table_name or "").strip().lower()
    if tn and tn in blob:
        score += 50
    src = (file_content or "").lower()
    clues = _clue_text(skill.get("content") or "").lower()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}|[\u4e00-\u9fff]{2,}", clues)
    seen: set[str] = set()
    for tok in tokens:
        t = tok.lower()
        if t in seen or t in _STOP:
            continue
        seen.add(t)
        if t in src:
            score += 4
    for c in columns or []:
        field = (getattr(c, "field", "") or "").lower()
        title = (getattr(c, "title", "") or "").lower()
        if field and field in blob:
            score += 5
        if title and len(title) >= 2 and title in blob:
            score += 2
    return score


def pick_by_rules(
    skills: list[dict],
    *,
    table_name: str,
    columns: list[ColumnDef],
    file_content: str,
    min_score: int = 18,
) -> dict | None:
    if not skills:
        return None
    ranked = []
    for s in skills:
        ranked.append((score_skill(s, table_name=table_name, columns=columns, file_content=file_content), s))
    ranked.sort(key=lambda x: x[0], reverse=True)
    best_score, best = ranked[0]
    second = ranked[1][0] if len(ranked) > 1 else 0
    if best_score < min_score:
        return None
    if second and best_score - second < 4 and best_score < 40:
        return None
    return best


def pick_by_llm(
    skills: list[dict],
    *,
    table_name: str,
    columns: list[ColumnDef],
    file_content: str,
    cfg: dict,
) -> tuple[dict | None, str]:
    if not skills or not cfg or not cfg.get("api_key") or not cfg.get("model"):
        return None, ""
    catalog = [
        {"id": s["id"], "name": s.get("name") or "", "excerpt": (s.get("content") or "")[:800]}
        for s in skills
    ]
    col_txt = "、".join(f"{c.field}({c.title})" for c in (columns or [])[:40])
    prompt = (
        "你是导入 Skill 路由器。从候选中选最匹配当前源文件与目标表的一个 skill_id；"
        "没有把握则 skill_id 为 null。只输出 JSON。\n"
        f"目标表：{table_name or ''}\n"
        f"列：{col_txt}\n"
        f"源文件节选：\n{(file_content or '')[:6000]}\n"
        f"候选：{json.dumps(catalog, ensure_ascii=False)}"
    )
    try:
        client = OpenAI(base_url=cfg.get("base_url") or None, api_key=cfg["api_key"], timeout=30)
        resp = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {"role": "system", "content": "只输出 JSON：{\"skill_id\": 数字或 null, \"reason\": \"一句\"}"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        raw = resp.choices[0].message.content or ""
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0) if m else raw)
        sid = data.get("skill_id")
        reason = str(data.get("reason") or "模型路由")
        if sid is None or sid == "":
            return None, reason
        picked = next((s for s in skills if int(s["id"]) == int(sid)), None)
        return picked, reason
    except Exception:
        return None, ""


def _pack(skill: dict | None, *, auto: bool, reason: str) -> dict:
    if not skill:
        return {
            "skill_id": None,
            "skill_name": None,
            "skill_auto": auto,
            "skill_reason": reason,
            "skill_content": None,
        }
    return {
        "skill_id": skill["id"],
        "skill_name": skill.get("name") or "",
        "skill_auto": auto,
        "skill_reason": reason,
        "skill_content": skill.get("content") or "",
    }


def resolve_skill(
    skills: list[dict],
    *,
    skill_id: int | None,
    auto_skill: bool,
    table_name: str,
    columns: list[ColumnDef],
    file_content: str,
    use_llm: bool = False,
    llm_cfg: dict | None = None,
) -> dict:
    if skill_id:
        skill = next((s for s in skills if int(s["id"]) == int(skill_id)), None)
        if skill:
            return _pack(skill, auto=False, reason="用户指定")
        return _pack(None, auto=False, reason="指定的 Skill 不存在，改用基线")
    if not auto_skill:
        return _pack(None, auto=False, reason="用户选择仅基线")
    if use_llm and llm_cfg:
        picked, reason = pick_by_llm(
            skills,
            table_name=table_name,
            columns=columns,
            file_content=file_content,
            cfg=llm_cfg,
        )
        if picked:
            return _pack(picked, auto=True, reason=reason or "自动匹配（模型）")
    picked = pick_by_rules(
        skills,
        table_name=table_name,
        columns=columns,
        file_content=file_content,
    )
    if not picked:
        return _pack(None, auto=True, reason="未匹配到 Skill，仅用基线")
    return _pack(picked, auto=True, reason="自动匹配（规则打分）")
