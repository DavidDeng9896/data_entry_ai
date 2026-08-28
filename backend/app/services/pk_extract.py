"""从解析正文中抽出 PK 主源，以及 mock 下的 WinNonlin 均值抽取。"""
from __future__ import annotations

import re
import statistics

from ..schemas import ColumnDef

_FOCUS = re.compile(
    r"cover|封面|pk 参数|pk parameters|试验设计|study design|data summary|结果汇总",
    re.I,
)
_SKIP = re.compile(r"raw data|原始数据|lc-ms|标曲|formulation|clinical observation", re.I)
_HW = re.compile(r"HW[\w\-]+", re.I)
_SKIP_ROW = re.compile(
    r"^(n|sd|cv|cv\s*\(%\)|g\d+-sd|g\d+-cv|animal no\.?|sort)$",
    re.I,
)


def focus_content_for_model(content: str) -> str:
    """只送给模型封面 + PK 参数 + 试验设计。原始数据/LC-MS 不送，避免一次请求过大导致 504。"""
    parts = [p for p in re.split(r"(?=^### )", content or "", flags=re.M) if p.strip()]
    if not parts:
        return content or ""
    kept = []
    for p in parts:
        head = p.splitlines()[0]
        if _SKIP.search(head):
            continue
        if _FOCUS.search(head):
            kept.append(p)
    if kept:
        return "\n".join(kept)
    return content or ""


def _clean(s: str) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(s or "")).strip()


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9%]+", "", _clean(s).lower())


def _to_float(s: str) -> float | None:
    t = _clean(s).replace(",", "")
    if not t or t.lower() in {"nan", "na", "n/a", "nd", "blq", "/", "-"}:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _mean(vals: list[float]) -> str:
    nums = [v for v in vals if v is not None]
    if not nums:
        return ""
    v = statistics.fmean(nums)
    if abs(v) >= 100:
        return f"{v:.2f}"
    return f"{v:.4f}".rstrip("0").rstrip(".")


def _parse_md_tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    cur: list[list[str]] = []
    for line in (text or "").splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells):
                continue
            cur.append(cells)
        elif cur:
            tables.append(cur)
            cur = []
    if cur:
        tables.append(cur)
    return tables


def _header_index(header: list[str], *needles: str, exclude: tuple[str, ...] = ()) -> int | None:
    norm = [_norm(h) for h in header]
    excl = [_norm(x) for x in exclude]
    want = [_norm(n) for n in needles]
    for i, h in enumerate(norm):
        if any(e and e in h for e in excl):
            continue
        if any(n and n in h for n in want):
            return i
    return None


def _ml_to_l_factor(cell: str) -> float:
    h = _norm(cell)
    if "ml" in h:
        return 0.001
    return 1.0


def _fill(row: dict, columns: list[ColumnDef]) -> dict:
    out = {c.field: "" for c in columns}
    for k, v in row.items():
        if k in out and v is not None:
            out[k] = str(v)
    return out


def _guess_species(text: str) -> str | None:
    t = (text or "").lower()
    monkey_hits = sum(
        1
        for s in ("食蟹猴", "cynomolgus", "to monkey", "monkey plasma", "食蟹猴药代", "administrations to monkey")
        if s in t
    )
    dog_hits = sum(1 for s in ("比格犬", "beagle", "dpk检测", "dpk检测报告") if s in t)
    if "dpk" in t and "猴" not in t and "monkey" not in t:
        dog_hits += 1
    if monkey_hits and monkey_hits >= dog_hits:
        return "monkey"
    if dog_hits:
        return "dog"
    return None


def _target_species(table_name: str) -> str | None:
    t = (table_name or "").lower()
    if "monkey" in t or "猴" in t:
        return "monkey"
    if "dog" in t or "犬" in t:
        return "dog"
    if "mouse" in t or "小鼠" in t:
        return "mouse"
    if "rat" in t or "大鼠" in t:
        return "rat"
    return None


def _find_cpds_id(text: str) -> str:
    m = re.search(r"### 文件:[^\n]*(HW[\w\-]+)", text or "")
    if m:
        return m.group(1)
    m = re.search(r"Test article\s*\|\s*(HW[\w\-]+)", text or "", re.I)
    if m:
        return m.group(1)
    m = re.search(r"化合物名称[:：]?\s*\|\s*(HW[\w\-]+)", text or "")
    if m:
        return m.group(1)
    m = re.search(r"化合物名称[:：]\s*(HW[\w\-]+)", text or "")
    if m:
        return m.group(1)
    found = _HW.findall(text or "")
    return found[0] if found else ""


def _po_dose_from_columns(columns: list[ColumnDef]) -> float:
    for c in columns:
        m = re.match(r"po_(\d+(?:\.\d+)?)_?mpk", c.field)
        if m:
            return float(m.group(1))
    return 5.0


class _Acc:
    def __init__(self):
        self.iv = {k: {"mean": [], "n": []} for k in ("cl", "vss", "auc", "t12", "dose")}
        self.po = {k: {"mean": [], "n": []} for k in ("cmax", "tmax", "auc", "t12", "f", "dose")}

    def add(self, route: str, kind: str, key: str, val: float | None):
        if val is None:
            return
        bucket = self.iv if route == "IV" else self.po
        if key not in bucket:
            return
        bucket[key][kind].append(val)

    def pick(self, route: str, key: str) -> list[float]:
        bucket = self.iv if route == "IV" else self.po
        if bucket[key]["mean"]:
            return bucket[key]["mean"]
        return bucket[key]["n"]


def _row_route(row: list[str]) -> str:
    for c in row[:6]:
        u = _clean(c).upper()
        if u in {"IV", "PO"}:
            return u
    return ""


def _parse_summary_table(table: list[list[str]], acc: _Acc) -> bool:
    blob = " ".join(" ".join(r[:8]) for r in table[:8]).lower()
    if "administration route" not in blob and "animal no" not in blob:
        return False
    hdr = None
    for row in table[:8]:
        joined = _norm(" ".join(row))
        if "auclast" in joined or "hl_lambda" in joined or "t12" in joined.replace("t1/2", "t12"):
            if _header_index(row, "tmax") is not None:
                hdr = row
                break
    if hdr is None:
        return False
    i_t12 = _header_index(hdr, "hl_lambda_z", "t1/2", "t12")
    i_tmax = _header_index(hdr, "tmax")
    i_cmax = _header_index(hdr, "cmax", exclude=("cmaxd", "cmax_d"))
    i_auc = _header_index(hdr, "auclast", "auc0-t", "auc(0-t)", exclude=("auclastd", "aucinf"))
    i_cl = _header_index(hdr, "cl_obs", "cl(", exclude=("clf", "clpred", "cl_f"))
    i_vss = _header_index(hdr, "vss_obs", "vss", exclude=("vsspred", "vss_pred"))
    i_f = _header_index(hdr, "f(%)", " f ", "%f")
    if i_cl is None:
        # 单位行/别名行上可能只有 Cl
        for row in table[:6]:
            idx = _header_index(row, "cl_obs")
            if idx is not None:
                i_cl = idx
                if i_vss is None:
                    i_vss = _header_index(row, "vss_obs")
                break
    cl_f = _ml_to_l_factor(hdr[i_cl]) if i_cl is not None and i_cl < len(hdr) else 1.0
    vss_f = _ml_to_l_factor(hdr[i_vss]) if i_vss is not None and i_vss < len(hdr) else 1.0
    if cl_f == 1.0:
        for row in table[:6]:
            if i_cl is not None and i_cl < len(row) and "ml" in _norm(row[i_cl]):
                cl_f = 0.001
            if i_vss is not None and i_vss < len(row) and "ml" in _norm(row[i_vss]):
                vss_f = 0.001

    used = False
    for row in table:
        if not row:
            continue
        c0 = _clean(row[0])
        if _SKIP_ROW.match(c0) or "animal" in c0.lower():
            continue
        blob_row = " ".join(row).lower()
        if "administration route" in blob_row or "dose level" in blob_row:
            continue
        route = _row_route(row)
        if not route:
            g = re.sub(r"\D", "", c0)
            if g.startswith("1") and len(g) == 3:
                route = "IV"
            elif g.startswith("2") and len(g) == 3:
                route = "PO"
        if not route:
            continue
        kind = "mean" if "mean" in c0.lower() else "n"
        if kind == "n" and not (c0.isdigit() or re.match(r"^g\d+", c0, re.I) or not c0):
            if not re.search(r"\d", c0):
                continue

        def cell(idx):
            if idx is None or idx >= len(row):
                return ""
            return row[idx]

        t12 = _to_float(cell(i_t12))
        tmax = _to_float(cell(i_tmax))
        cmax = _to_float(cell(i_cmax))
        auc = _to_float(cell(i_auc))
        cl = _to_float(cell(i_cl))
        vss = _to_float(cell(i_vss))
        fval = _to_float(cell(i_f)) if i_f is not None else None
        # G2 表头把 F 放在 C0 列位置
        if route == "PO" and fval is None:
            # 常见：C0 列在 IV 段是 C0，PO 段同一索引是 F
            i_c0 = _header_index(hdr, "c0")
            if i_c0 is not None:
                maybe = _to_float(cell(i_c0))
                # %F 一般 0–200；C0 常 >200
                if maybe is not None and maybe <= 200:
                    fval = maybe
        dose = None
        for idx in range(min(4, len(row))):
            d = _to_float(row[idx])
            if d in (1.0, 5.0, 10.0, 30.0, 100.0):
                dose = d
                break
        if route == "IV":
            if cl is not None:
                acc.add("IV", kind, "cl", cl * cl_f)
            if vss is not None:
                acc.add("IV", kind, "vss", vss * vss_f)
            if auc is not None:
                acc.add("IV", kind, "auc", auc)
            if t12 is not None:
                acc.add("IV", kind, "t12", t12)
            if dose is not None:
                acc.add("IV", kind, "dose", dose)
            used = True
        else:
            if cmax is not None:
                acc.add("PO", kind, "cmax", cmax)
            if tmax is not None:
                acc.add("PO", kind, "tmax", tmax)
            if auc is not None:
                acc.add("PO", kind, "auc", auc)
            if t12 is not None:
                acc.add("PO", kind, "t12", t12)
            if fval is not None:
                acc.add("PO", kind, "f", fval)
            if dose is not None:
                acc.add("PO", kind, "dose", dose)
            used = True
    return used


def _parse_winnonlin_table(table: list[list[str]], acc: _Acc) -> bool:
    hdr_i = None
    for i, row in enumerate(table[:6]):
        blob = _norm(" ".join(row))
        if "auclast" in blob and ("clobs" in blob or "hllambda" in blob):
            hdr_i = i
            break
    if hdr_i is None:
        return False
    header = table[hdr_i]
    i_cl = _header_index(header, "clobs", exclude=("clf", "clpred"))
    i_vss = _header_index(header, "vssobs", exclude=("vsspred",))
    i_auc = _header_index(header, "auclast", exclude=("auclastd", "auclast_d"))
    i_t12 = _header_index(header, "hllambdaz")
    i_cmax = _header_index(header, "cmaxng", "cmax", exclude=("cmaxd", "cmax_d"))
    i_tmax = _header_index(header, "tmax")
    i_dose = _header_index(header, "dosemg", "dose")
    cl_f = _ml_to_l_factor(header[i_cl]) if i_cl is not None else 1.0
    vss_f = _ml_to_l_factor(header[i_vss]) if i_vss is not None else 1.0
    route = ""
    used = False
    for row in table[hdr_i + 1 :]:
        if not row:
            continue
        c0 = _clean(row[0]).upper()
        if c0 in {"IV", "PO"}:
            route = c0
            blob_h = _norm(" ".join(row))
            if "cmax" in blob_h or "auclast" in blob_h or "dose" in blob_h:
                header = row
                i_cl = _header_index(header, "clobs", exclude=("clf", "clpred"))
                i_vss = _header_index(header, "vssobs", exclude=("vsspred",))
                i_auc = _header_index(header, "auclast", exclude=("auclastd", "auclast_d"))
                i_t12 = _header_index(header, "hllambdaz")
                i_cmax = _header_index(header, "cmaxng", "cmax", exclude=("cmaxd", "cmax_d"))
                i_tmax = _header_index(header, "tmax")
                i_dose = _header_index(header, "dosemg", "dose")
            continue
        blob = " ".join(row).lower()
        if "sort" in blob and "rsq" in blob:
            continue
        c0s = _clean(row[0])
        if _SKIP_ROW.match(c0s):
            continue

        def cell(idx):
            if idx is None or idx >= len(row):
                return ""
            return row[idx]

        dose = _to_float(cell(i_dose))
        g = re.sub(r"\D", "", c0s)
        is_iv = route == "IV" or (g.startswith("1") and len(g) == 3)
        is_po = route == "PO" or (g.startswith("2") and len(g) == 3)
        if dose == 5:
            is_po, is_iv = True, False
        elif dose == 1:
            is_iv, is_po = True, False
        if not is_iv and not is_po:
            continue
        cl = _to_float(cell(i_cl))
        vss = _to_float(cell(i_vss))
        auc = _to_float(cell(i_auc))
        t12 = _to_float(cell(i_t12))
        cmax = _to_float(cell(i_cmax))
        tmax = _to_float(cell(i_tmax))
        if is_iv:
            if cl is not None:
                acc.add("IV", "n", "cl", cl * cl_f)
            if vss is not None:
                acc.add("IV", "n", "vss", vss * vss_f)
            if auc is not None:
                acc.add("IV", "n", "auc", auc)
            if t12 is not None:
                acc.add("IV", "n", "t12", t12)
            if dose is not None:
                acc.add("IV", "n", "dose", dose)
            used = True
        if is_po:
            if cmax is not None:
                acc.add("PO", "n", "cmax", cmax)
            if tmax is not None:
                acc.add("PO", "n", "tmax", tmax)
            if auc is not None:
                acc.add("PO", "n", "auc", auc)
            if t12 is not None:
                acc.add("PO", "n", "t12", t12)
            if dose is not None:
                acc.add("PO", "n", "dose", dose)
            used = True
    return used


def _has_pk_columns(columns: list[ColumnDef]) -> bool:
    fields = {c.field for c in columns}
    return "iv_1mpk_cl_l_h_kg" in fields or any(f.startswith("po_") and "cmax" in f for f in fields)


def extract_pk_rows(
    content: str,
    columns: list[ColumnDef],
    table_name: str = "",
) -> tuple[list[dict] | None, str]:
    """mock PK 抽取。非 PK 列返回 (None, '')；种属不符返回空行。"""
    if not _has_pk_columns(columns):
        return None, ""
    text = content or ""
    if not re.search(r"PK 参数|PK parameters|Cl_obs|AUClast|HL_Lambda", text, re.I):
        return [], "未找到 PK 参数表，已跳过"

    want = _target_species(table_name)
    got = _guess_species(text)
    if want and got and want != got:
        return [], f"源文件种属（{got}）与目标表（{table_name}）不符，已跳过"

    acc = _Acc()
    tables = _parse_md_tables(text)
    used_summary = False
    for table in tables:
        if _parse_summary_table(table, acc):
            used_summary = True
            break
    if not used_summary or not acc.pick("IV", "cl"):
        acc2 = _Acc() if used_summary else acc
        got_w = False
        for table in tables:
            if _parse_winnonlin_table(table, acc2):
                got_w = True
        if got_w and used_summary and not acc.pick("IV", "cl"):
            acc = acc2
        elif got_w and not used_summary:
            acc = acc2

    cpds = _find_cpds_id(text)
    iv_dose = acc.pick("IV", "dose")
    po_dose = acc.pick("PO", "dose")
    iv_auc = acc.pick("IV", "auc")
    po_auc = acc.pick("PO", "auc")
    fvals = acc.pick("PO", "f")
    pct_f = _mean(fvals)
    if not pct_f and iv_auc and po_auc:
        d_iv = statistics.fmean(iv_dose) if iv_dose else 1.0
        d_po = statistics.fmean(po_dose) if po_dose else _po_dose_from_columns(columns)
        if d_iv and d_po:
            f = (statistics.fmean(po_auc) / d_po) / (statistics.fmean(iv_auc) / d_iv) * 100.0
            pct_f = _mean([f])

    row = {
        "cpds_id": cpds,
        "iv_1mpk_cl_l_h_kg": _mean(acc.pick("IV", "cl")),
        "iv_1mpk_vss_l_kg": _mean(acc.pick("IV", "vss")),
        "iv_1mpk_auc0_t_h_ng_ml": _mean(acc.pick("IV", "auc")),
        "iv_1mpk_t1_2_hr": _mean(acc.pick("IV", "t12")),
        "po_5_mpk_cmax_ng_ml": _mean(acc.pick("PO", "cmax")),
        "po_5_mpk_tmax_hr": _mean(acc.pick("PO", "tmax")),
        "po_5_mpk_auc0_t_h_ng_ml": _mean(acc.pick("PO", "auc")),
        "po_5_mpk_t1_2_hr": _mean(acc.pick("PO", "t12")),
        "po_5_mpk_pct_f": pct_f,
    }
    if not row["cpds_id"] and not any(row[k] for k in row if k != "cpds_id"):
        return [], "未能从 PK 参数解析到数据"
    return [_fill(row, columns)], f"mock：已从 PK 参数表抽取 {row['cpds_id'] or '1'} 行（动物均值）"


def mock_extract_pk(
    content: str,
    columns: list[ColumnDef],
    table_name: str = "",
) -> tuple[list[dict], str] | None:
    rows, note = extract_pk_rows(content, columns, table_name=table_name)
    if rows is None:
        return None
    return rows, note
