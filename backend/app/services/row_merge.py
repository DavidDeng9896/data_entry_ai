"""分页/多附件抽出的行按化合物 ID 合并；冲突保留首值并标记。"""
from __future__ import annotations

import math
import re


def _blank(v) -> bool:
    return v is None or str(v).strip() == ""


def _norm_key(v) -> str:
    return re.sub(r"\s+", "", str(v or "")).upper()


def _values_equal(a, b) -> bool:
    sa, sb = str(a).strip(), str(b).strip()
    if sa == sb:
        return True
    try:
        fa, fb = float(sa.replace(",", "")), float(sb.replace(",", ""))
    except ValueError:
        return False
    if math.isnan(fa) or math.isnan(fb):
        return False
    scale = max(abs(fa), abs(fb), 1e-9)
    return abs(fa - fb) / scale < 1e-3


def merge_extracted_rows(rows: list[dict], *, key_field: str = "cpds_id") -> tuple[list[dict], list[dict]]:
    """同一 key 合并为一行。空值被填上；两边都有且不等 → 保留先到的值，记入冲突。"""
    merged: list[dict] = []
    index: dict[str, int] = {}
    conflicts: list[dict] = []

    for raw in rows or []:
        row = {k: v for k, v in (raw or {}).items() if k != "_conflicts"}
        key = _norm_key(row.get(key_field))
        if not key:
            merged.append(dict(row))
            continue
        if key not in index:
            index[key] = len(merged)
            merged.append(dict(row))
            continue
        dest = merged[index[key]]
        dest_conflicts = dict(dest.get("_conflicts") or {})
        for field, val in row.items():
            if field == key_field or _blank(val):
                continue
            old = dest.get(field)
            if _blank(old):
                dest[field] = val
                continue
            if _values_equal(old, val):
                continue
            seen = dest_conflicts.setdefault(field, [str(old).strip()])
            nv = str(val).strip()
            if nv not in seen:
                seen.append(nv)
            conflicts.append({
                "cpds_id": dest.get(key_field) or key,
                "field": field,
                "kept": str(old).strip(),
                "others": [nv],
            })
        if dest_conflicts:
            dest["_conflicts"] = dest_conflicts

    # 去重 conflicts 同 field
    uniq = []
    seen_cf = set()
    for c in conflicts:
        k = (c["cpds_id"], c["field"], c["kept"])
        if k in seen_cf:
            continue
        seen_cf.add(k)
        uniq.append(c)
    return merged, uniq


def summarize_chunk_notes(chunks: list[tuple[str, list[dict]]]) -> str:
    """只保留抽出了行的分段说明，避免封面/方法页的「找不到主源」盖过结论。"""
    total = len(chunks)
    filled = [(i, note, rows) for i, (note, rows) in enumerate(chunks, 1) if rows]
    empty_n = total - len(filled)
    lines = [
        f"共 {total} 段：{len(filled)} 段抽出数据"
        + (f"，{empty_n} 段为封面/方法等无结果（已忽略，避免和表内数据矛盾）。" if empty_n else "。")
    ]
    if empty_n and filled:
        empty_idx = [str(i) for i, (note, rows) in enumerate(chunks, 1) if not rows]
        lines.append(f"无数据段：第 {', '.join(empty_idx)} 段。")
    for i, note, rows in filled:
        brief = (note or "").strip()
        if len(brief) > 600:
            brief = brief[:600] + "…"
        lines.append(f"第 {i} 段抽出 {len(rows)} 行：")
        if brief:
            lines.append(brief)
    if not filled:
        lines.append("各段均未抽出结果行。")
    return "\n".join(lines)
