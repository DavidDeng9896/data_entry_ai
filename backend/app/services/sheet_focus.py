"""按 Skill「读取范围」裁 sheet；无 Skill 时按页名自判结论页 vs 过程页。"""
from __future__ import annotations

import re

_READ_SEC = re.compile(r"##\s*读取范围([\s\S]*?)(?:\n##\s|\Z)")
_SELF_SKIP = re.compile(
    r"raw\s*data|原始数据|标曲|质控|lc-?ms|formulation|clinical\s*observation|"
    r"试验设计|study\s*design|给药制剂",
    re.I,
)
_SELF_KEEP = re.compile(
    r"cover|封面|signature|summary|汇总|参数|parameter|assay|ic50|"
    r"remaining|papp|solubility",
    re.I,
)


def _split_parts(content: str) -> list[str]:
    return [p for p in re.split(r"(?=^### )", content or "", flags=re.M) if p.strip()]


def _sheet_title(part: str) -> str:
    head = part.splitlines()[0]
    m = re.search(r"###\s*(?:Sheet:\s*)?(.+)$", head)
    return (m.group(1) if m else head).strip()


def _norm(name: str) -> str:
    return re.sub(r"\s+", "", name or "").lower()


def _listed(name: str, tokens: list[str]) -> bool:
    n = _norm(name)
    if not n:
        return False
    for raw in tokens:
        t = _norm(raw)
        if t and (t in n or n in t):
            return True
    return False


def parse_sheet_policy(skill_content: str | None) -> dict | None:
    """从 Skill 的「读取范围」抽出 include / skip 页名。没有该节则返回 None。"""
    m = _READ_SEC.search(skill_content or "")
    if not m:
        return None
    include: list[str] = []
    skip: list[str] = []
    for line in m.group(1).splitlines():
        names = [n.strip() for n in re.findall(r"`([^`]+)`", line) if n.strip()]
        if not names:
            continue
        if re.search(r"跳过|不读|忽略", line):
            skip.extend(names)
        else:
            include.extend(names)
    if not include and not skip:
        return None
    return {"include": include, "skip": skip}


def _keep_by_skill(parts: list[str], policy: dict) -> list[str]:
    include = policy.get("include") or []
    skip = policy.get("skip") or []
    kept = []
    for p in parts:
        title = _sheet_title(p)
        if skip and _listed(title, skip):
            continue
        if include:
            if _listed(title, include):
                kept.append(p)
        else:
            kept.append(p)
    return kept


def _keep_by_self(parts: list[str]) -> list[str]:
    kept = []
    rest = []
    for p in parts:
        title = _sheet_title(p)
        if _SELF_SKIP.search(title):
            continue
        if _SELF_KEEP.search(title):
            kept.append(p)
        else:
            rest.append(p)
    if kept:
        return kept
    return rest or parts


def focus_content_for_model(content: str, skill_content: str | None = None) -> str:
    """有 Skill 读取范围则按其裁页；否则按页名自判。裁完为空则退回原文。"""
    parts = _split_parts(content)
    if not parts:
        return content or ""
    policy = parse_sheet_policy(skill_content)
    if policy:
        kept = _keep_by_skill(parts, policy)
    else:
        kept = _keep_by_self(parts)
    if kept:
        return "\n".join(kept)
    return content or ""
