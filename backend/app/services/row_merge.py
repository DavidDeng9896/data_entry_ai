"""分页摘要与可选的按调用方指定键合并（生产路径默认不合并）。"""
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
    return abs(fa - fb) / scale < 1e-2


def _row_merge_key(row: dict, key_fields: list[str]) -> str:
    parts = [_norm_key(row.get(f)) for f in key_fields]
    if not any(parts):
        return ""
    return "\x00".join(parts)


def _row_identity_label(row: dict, key_fields: list[str]) -> str:
    vals = [str(row.get(f) or "").strip() for f in key_fields if not _blank(row.get(f))]
    return " / ".join(vals) if vals else ""


def merge_extracted_rows(
    rows: list[dict],
    *,
    key_field: str = "cpds_id",
    key_fields: list[str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """同一复合键合并为一行。空值被填上；两边都有且不等 → 保留先到的值，记入冲突。"""
    fields = list(key_fields or [key_field])
    merged: list[dict] = []
    index: dict[str, int] = {}
    conflicts: list[dict] = []

    for raw in rows or []:
        incoming_conflicts = dict((raw or {}).get("_conflicts") or {})
        row = {k: v for k, v in (raw or {}).items() if k != "_conflicts"}
        key = _row_merge_key(row, fields)
        if not key:
            item = dict(row)
            if incoming_conflicts:
                item["_conflicts"] = incoming_conflicts
            merged.append(item)
            continue
        if key not in index:
            index[key] = len(merged)
            item = dict(row)
            if incoming_conflicts:
                item["_conflicts"] = incoming_conflicts
            merged.append(item)
            continue
        dest = merged[index[key]]
        dest_conflicts = dict(dest.get("_conflicts") or {})
        for field, vals in incoming_conflicts.items():
            seen = dest_conflicts.setdefault(field, [])
            for v in vals if isinstance(vals, list) else [vals]:
                sv = str(v).strip()
                if sv and sv not in seen:
                    seen.append(sv)
        for field, val in row.items():
            if field in fields or _blank(val):
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
                "cpds_id": _row_identity_label(dest, fields) or key,
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
        + (f"，{empty_n} 段无抽出结果（已忽略，避免和表内数据矛盾）。" if empty_n else "。")
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


def compose_extraction_reply(
    chunk_notes: list[tuple[str, list[dict]]],
    merged: list[dict],
    *,
    raw_n: int,
    n_items: int,
    new_conflicts: list[dict],
) -> str:
    """多附件时隐藏空文件说明；单附件沿用内层分页摘要。"""
    if n_items > 1:
        reply = summarize_chunk_notes(chunk_notes)
    else:
        reply = (chunk_notes[0][0] if chunk_notes else "") or ""
    if not (reply or "").strip():
        reply = f"合计 {len(merged)} 行。"
    extras: list[str] = []
    if new_conflicts:
        extras.append(f"有 {len(new_conflicts)} 处取值不一致，已标黄，请核对后再确认导入。")
    if extras:
        reply = reply.rstrip() + "\n" + "\n".join(extras)
    return reply
