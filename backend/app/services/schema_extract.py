"""解析 <<<SCHEMA>>> 块、清洗列、按草稿决定回写。"""
import json
import re

from .schema_intent import wants_meta_change

ALLOWED_TYPES = {"text", "number", "date", "select"}


def _norm_field(raw: str) -> str:
    s = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    return re.sub(r"[^a-z0-9_]", "", s)


def sanitize_columns(raw) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        field = _norm_field(str(item.get("field") or ""))
        title = str(item.get("title") or "").strip()
        if not field or not title or field in seen:
            continue
        seen.add(field)
        typ = item.get("type") if item.get("type") in ALLOWED_TYPES else "text"
        options = item.get("options") or []
        if not isinstance(options, list):
            options = []
        options = [str(x).strip() for x in options if str(x).strip()]
        out.append({
            "field": field,
            "title": title,
            "type": typ,
            "required": bool(item.get("required")),
            "options": options if typ == "select" else [],
            "description": str(item.get("description") or "").strip(),
        })
    return out


def _try_schema_obj(text: str) -> dict | None:
    blob = (text or "").strip()
    if not blob:
        return None
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", blob)
    if fence:
        blob = fence.group(1).strip()
    start = blob.find("{")
    end = blob.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(blob[start:end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def split_schema_reply(raw: str) -> tuple[str, dict | None]:
    text = (raw or "").strip()
    if "<<<SCHEMA>>>" not in text:
        parsed = _try_schema_obj(text)
        return text, parsed
    pieces = text.split("<<<SCHEMA>>>")
    note = pieces[0].strip()
    parsed = None
    for piece in reversed(pieces[1:]):
        body = piece.split("<<<END>>>")[0]
        parsed = _try_schema_obj(body)
        if parsed is not None:
            break
    return note or text, parsed


def compose_schema_response(intent: str, reply: str, parsed: dict | None, draft: dict, last_user: str) -> dict:
    draft = draft or {}
    draft_name = str(draft.get("name") or "")
    draft_desc = str(draft.get("description") or "")
    base = {
        "reply": reply or "",
        "intent": intent,
        "name": draft_name,
        "description": draft_desc,
        "columns": [],
        "skill_name": str(draft.get("skill_name") or ""),
        "skill_md": str(draft.get("skill_md") or ""),
    }
    if intent != "schema" or not parsed:
        return base
    columns = sanitize_columns(parsed.get("columns"))
    if not columns:
        return base
    apply_meta = wants_meta_change(last_user)
    name = str(parsed.get("name") or "").strip()
    desc = str(parsed.get("description") or "").strip()
    if apply_meta or not draft_name.strip():
        base["name"] = name or draft_name
    if apply_meta or not draft_desc.strip():
        base["description"] = desc or draft_desc
    base["columns"] = columns
    base["skill_name"] = str(parsed.get("skill_name") or "").strip() or base["skill_name"]
    base["skill_md"] = str(parsed.get("skill_md") or "").strip() or base["skill_md"]
    return base
