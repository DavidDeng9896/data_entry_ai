"""对已填入结果表的格子做本地修改，不重新跑识别。"""
from __future__ import annotations

import copy
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from ..schemas import ColumnDef

_SKIP_FIELDS = {"cpds_id"}
_NUM = re.compile(
    r"^(?P<prefix>[<>]=?)?\s*(?P<num>[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*$"
)
_PLACES = re.compile(
    r"(?:超过|保留|改成|改为|到)?\s*(\d+)\s*位(?:小数)?"
    r"|(\d+)\s*位小数"
    r"|两位小数|2位小数"
)


def parse_decimal_places(instruction: str) -> int | None:
    t = instruction or ""
    if re.search(r"两位小数|2位小数", t):
        return 2
    m = _PLACES.search(t)
    if not m:
        return None
    for g in m.groups():
        if g:
            return int(g)
    return None


def looks_like_local_edit(instruction: str) -> bool:
    t = instruction or ""
    if re.search(r"小数|四舍五入|位数", t) and re.search(r"改|保留|超过|位", t):
        return True
    if parse_decimal_places(t) is not None and re.search(r"改|保留|超过|四舍五入|小数", t):
        return True
    return False


def _decimal_count(num: str) -> int:
    if "." not in num:
        return 0
    frac = num.split(".", 1)[1]
    frac = re.split(r"[eE]", frac, maxsplit=1)[0]
    return len(frac)


def _round_token(raw: str, places: int) -> str | None:
    s = (raw or "").strip()
    if not s:
        return None
    m = _NUM.match(s)
    if not m:
        return None
    num = m.group("num")
    if _decimal_count(num) <= places:
        return None
    try:
        d = Decimal(num)
    except (InvalidOperation, ValueError):
        return None
    q = Decimal("1").scaleb(-places)
    rounded = d.quantize(q, rounding=ROUND_HALF_UP)
    text = format(rounded, "f")
    if places == 0:
        text = str(int(rounded))
    prefix = m.group("prefix") or ""
    return f"{prefix}{text}"


def round_excess_decimals(rows: list[dict], columns: list[ColumnDef], places: int) -> tuple[list[dict], int]:
    fields = [c.field for c in (columns or []) if c.field and c.field not in _SKIP_FIELDS]
    if not fields:
        fields = [k for row in rows for k in row.keys() if k not in _SKIP_FIELDS and not str(k).startswith("_")]
        fields = list(dict.fromkeys(fields))
    out = []
    changed = 0
    for row in rows:
        new_row = copy.deepcopy(row)
        for field in fields:
            val = new_row.get(field)
            if val is None or val == "":
                continue
            nxt = _round_token(str(val), places)
            if nxt is not None and nxt != str(val).strip():
                new_row[field] = nxt
                changed += 1
        out.append(new_row)
    return out, changed


def apply_local_edit(instruction: str, rows: list[dict], columns: list[ColumnDef]) -> tuple[str, list[dict], bool]:
    """成功则 (回复, 新行, True)；无法本地处理则 (原因, 原行, False)。"""
    if not rows:
        return "当前表还没有已填入的数据，请先识别后再改格子。", rows, False
    places = parse_decimal_places(instruction)
    if places is None:
        return "", rows, False
    new_rows, n = round_excess_decimals(rows, columns, places)
    if n == 0:
        return f"当前已填格子里没有超过 {places} 位小数的数字，未改表，也没有重新识别。", rows, True
    return (
        f"已将 {n} 个超过 {places} 位小数的数字改为 {places} 位，只改了已填格子，没有重新识别附件。",
        new_rows,
        True,
    )
