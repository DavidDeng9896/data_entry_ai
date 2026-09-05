"""按 Skill「读取范围」裁 sheet；无 Skill 时按页名自判结论页 vs 过程页。

裁页只看真正的内容块（Sheet / 第 N 页）。文件名包装、标题像文件名的块
不参与 keep/skip。裁完若没有有效正文，退回原文，避免只剩文件名。
"""
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
    r"result|remaining|papp|solubility",
    re.I,
)
_FILE_WRAP = re.compile(r"^###\s*文件:")
_FILE_EXT = re.compile(
    r"\.(xlsx|xlsm|xls|csv|tsv|pdf|docx?|pptx?|png|jpe?g|zip)\s*$",
    re.I,
)
_PAGE_HEAD = re.compile(r"^###\s*第\s*\d+", re.I)


def _split_parts(content: str) -> list[str]:
    return [p for p in re.split(r"(?=^### )", content or "", flags=re.M) if p.strip()]


def _heading(part: str) -> str:
    return (part or "").splitlines()[0] if part else ""


def _is_file_wrapper(part: str) -> bool:
    return bool(_FILE_WRAP.match(_heading(part)))


def _sheet_title(part: str) -> str:
    head = _heading(part)
    m = re.search(r"###\s*(?:Sheet:\s*)?(.+)$", head)
    return (m.group(1) if m else head).strip()


def _looks_like_filename(name: str) -> bool:
    return bool(_FILE_EXT.search((name or "").strip()))


def _is_meta_part(part: str) -> bool:
    """包装行或标题本身是文件名：不当成 sheet 来筛选。"""
    if _is_file_wrapper(part):
        return True
    if _PAGE_HEAD.match(_heading(part)):
        return False
    title = _sheet_title(part)
    if _looks_like_filename(title):
        return True
    # `### 某文件.xlsx` 且正文几乎没有表格
    if _looks_like_filename(_heading(part).lstrip("# ").strip()):
        return True
    return False


def _part_body(part: str) -> str:
    lines = (part or "").splitlines()
    return "\n".join(lines[1:]).strip()


def _has_payload(parts: list[str]) -> bool:
    for p in parts:
        if _is_meta_part(p):
            continue
        if _part_body(p):
            return True
    return False


def _norm(name: str) -> str:
    return re.sub(r"\s+", "", name or "").lower()


def _listed(name: str, tokens: list[str]) -> bool:
    """只匹配页名，不匹配文件名。去空格后相等，或词是页名的连续片段。"""
    if _looks_like_filename(name):
        return False
    n = _norm(name)
    if not n:
        return False
    for raw in tokens:
        t = _norm(raw)
        if not t:
            continue
        if n == t:
            return True
        if t in n:
            return True
        if n in t and len(n) >= 2:
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
    """有 Skill 读取范围则按其裁页；否则按页名自判。裁完无正文则退回原文。"""
    parts = _split_parts(content)
    if not parts:
        return content or ""
    meta = [p for p in parts if _is_meta_part(p)]
    selectable = [p for p in parts if not _is_meta_part(p)]
    if not selectable:
        return content or ""
    policy = parse_sheet_policy(skill_content)
    if policy:
        kept = _keep_by_skill(selectable, policy)
    else:
        kept = _keep_by_self(selectable)
    if not _has_payload(kept):
        return content or ""
    prefix = [p for p in meta if _is_file_wrapper(p)][:1]
    return "\n".join(prefix + kept)
