"""SQLite 持久层：结果表定义、列配置、skills、settings 全部入库。
库文件：data/data_entry.db；首次启动自动建表并从旧 json/md 文件迁移。
"""
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .config import DATA_DIR, SKILLS_DIR, SETTINGS_FILE, COLUMNS_FILE, DEFAULT_COLUMNS

DB_FILE = DATA_DIR / "data_entry.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS result_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS columns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER NOT NULL REFERENCES result_tables(id) ON DELETE CASCADE,
    field TEXT NOT NULL,
    title TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'text',
    required INTEGER NOT NULL DEFAULT 0,
    options TEXT NOT NULL DEFAULT '[]',
    description TEXT NOT NULL DEFAULT '',
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 0,
    updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER NOT NULL REFERENCES result_tables(id) ON DELETE CASCADE,
    source_files TEXT NOT NULL DEFAULT '[]',
    skill_name TEXT NOT NULL DEFAULT '',
    row_count INTEGER NOT NULL DEFAULT 0,
    conflicts TEXT NOT NULL DEFAULT '[]',
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS imported_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id INTEGER NOT NULL REFERENCES result_tables(id) ON DELETE CASCADE,
    batch_id INTEGER NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
    data TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """建表 + 首次迁移旧文件数据"""
    with get_db() as conn:
        conn.executescript(SCHEMA)

        # 迁移结果表定义（来自 columns.json）
        if not conn.execute("SELECT 1 FROM result_tables LIMIT 1").fetchone():
            _migrate_tables(conn)

        # 迁移 skills（来自 skills/*.md）
        if not conn.execute("SELECT 1 FROM skills LIMIT 1").fetchone():
            _migrate_skills(conn)

        # 迁移 settings（来自 settings.json）
        if not conn.execute("SELECT 1 FROM settings WHERE key='model'").fetchone():
            _migrate_settings(conn)


def _migrate_tables(conn) -> None:
    data = {}
    if COLUMNS_FILE.exists():
        try:
            data = json.loads(COLUMNS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    if not data:
        data = DEFAULT_COLUMNS
    now = time.time()
    for name, cols in data.items():
        if not cols:
            continue
        # 旧文件里 key 是 result/registry，result 对应 Binding Assay
        display_name = "Binding Assay" if name == "result" else name
        cur = conn.execute(
            "INSERT INTO result_tables (name, description, created_at) VALUES (?, ?, ?)",
            (display_name, "", now)
        )
        table_id = cur.lastrowid
        for i, c in enumerate(cols):
            conn.execute(
                "INSERT INTO columns (table_id, field, title, type, required, options, description, sort_order) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (table_id, c["field"], c["title"], c.get("type", "text"),
                 1 if c.get("required") else 0,
                 json.dumps(c.get("options", []), ensure_ascii=False),
                 c.get("description", ""), i)
            )


def _migrate_skills(conn) -> None:
    if not SKILLS_DIR.exists():
        return
    now = time.time()
    for f in sorted(SKILLS_DIR.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        name = f.stem
        # 首行 # 标题优先
        for line in content.splitlines():
            if line.startswith("# "):
                name = line[2:].strip()
                break
        conn.execute(
            "INSERT INTO skills (name, content, enabled, updated_at) VALUES (?, ?, 0, ?)",
            (name, content, now)
        )


def _migrate_settings(conn) -> None:
    from .config import load_settings
    settings = load_settings()
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        ("model", json.dumps(settings, ensure_ascii=False))
    )


# ===== 结果表 CRUD =====

def list_tables() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT t.id, t.name, t.description, t.created_at, "
            "COUNT(DISTINCT c.id) AS column_count, "
            "COUNT(DISTINCT r.id) AS row_count "
            "FROM result_tables t "
            "LEFT JOIN columns c ON c.table_id = t.id "
            "LEFT JOIN imported_rows r ON r.table_id = t.id "
            "GROUP BY t.id ORDER BY t.created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_table(table_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT id, name, description, created_at FROM result_tables WHERE id = ?", (table_id,)).fetchone()
        return dict(row) if row else None


def create_table(name: str, description: str, columns: list[dict]) -> dict:
    with get_db() as conn:
        if conn.execute("SELECT 1 FROM result_tables WHERE name = ?", (name,)).fetchone():
            raise ValueError(f"结果表「{name}」已存在")
        cur = conn.execute(
            "INSERT INTO result_tables (name, description, created_at) VALUES (?, ?, ?)",
            (name, description or "", time.time())
        )
        table_id = cur.lastrowid
        _save_columns(conn, table_id, columns)
        return {"id": table_id, "name": name, "description": description}


def update_table(table_id: int, name: str | None = None, description: str | None = None) -> None:
    with get_db() as conn:
        if name is not None:
            dup = conn.execute("SELECT 1 FROM result_tables WHERE name = ? AND id != ?", (name, table_id)).fetchone()
            if dup:
                raise ValueError(f"结果表「{name}」已存在")
            conn.execute("UPDATE result_tables SET name = ? WHERE id = ?", (name, table_id))
        if description is not None:
            conn.execute("UPDATE result_tables SET description = ? WHERE id = ?", (description, table_id))


def delete_table(table_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM imported_rows WHERE table_id = ?", (table_id,))
        conn.execute("DELETE FROM import_batches WHERE table_id = ?", (table_id,))
        conn.execute("DELETE FROM columns WHERE table_id = ?", (table_id,))
        conn.execute("DELETE FROM result_tables WHERE id = ?", (table_id,))


def copy_table(table_id: int, new_name: str) -> dict:
    """复制某表的列配置为新表"""
    src = get_table(table_id)
    if not src:
        raise ValueError("源表不存在")
    cols = get_columns(table_id)
    return create_table(new_name, src["description"], cols)


# ===== 列配置 =====

def _save_columns(conn, table_id: int, columns: list[dict]) -> None:
    conn.execute("DELETE FROM columns WHERE table_id = ?", (table_id,))
    for i, c in enumerate(columns):
        conn.execute(
            "INSERT INTO columns (table_id, field, title, type, required, options, description, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (table_id, c["field"], c["title"], c.get("type", "text"),
             1 if c.get("required") else 0,
             json.dumps(c.get("options", []), ensure_ascii=False),
             c.get("description", ""), i)
        )


def get_columns(table_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT field, title, type, required, options, description FROM columns "
            "WHERE table_id = ? ORDER BY sort_order", (table_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["required"] = bool(d["required"])
            try:
                d["options"] = json.loads(d["options"])
            except Exception:
                d["options"] = []
            result.append(d)
        return result


def save_columns(table_id: int, columns: list[dict]) -> None:
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM result_tables WHERE id = ?", (table_id,)).fetchone():
            raise ValueError("结果表不存在")
        _save_columns(conn, table_id, columns)


# ===== Skills =====

def list_skills() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, enabled, updated_at FROM skills ORDER BY updated_at DESC").fetchall()
        return [dict(r) | {"enabled": bool(r["enabled"])} for r in rows]


def list_skills_full() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, content, enabled FROM skills ORDER BY updated_at DESC").fetchall()
        return [dict(r) | {"enabled": bool(r["enabled"])} for r in rows]


def get_skill(skill_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT id, name, content, enabled FROM skills WHERE id = ?", (skill_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["enabled"] = bool(d["enabled"])
        return d


def get_skill_content(skill_id: int) -> str | None:
    skill = get_skill(skill_id)
    return skill["content"] if skill else None


def save_skill(skill_id: int | None, name: str, content: str) -> int:
    with get_db() as conn:
        if skill_id:
            conn.execute(
                "UPDATE skills SET name = ?, content = ?, updated_at = ? WHERE id = ?",
                (name, content, time.time(), skill_id)
            )
            return skill_id
        cur = conn.execute(
            "INSERT INTO skills (name, content, enabled, updated_at) VALUES (?, ?, 0, ?)",
            (name, content, time.time())
        )
        return cur.lastrowid


def delete_skill(skill_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))


def set_enabled_skill(skill_id: int | None) -> None:
    """启用某个 skill（单选），传 None 全部取消"""
    with get_db() as conn:
        conn.execute("UPDATE skills SET enabled = 0")
        if skill_id is not None:
            conn.execute("UPDATE skills SET enabled = 1 WHERE id = ?", (skill_id,))


# ===== Settings =====

def load_model_settings() -> dict:
    from .config import DEFAULT_SETTINGS
    data = {}
    with get_db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'model'").fetchone()
        if row:
            try:
                data = json.loads(row["value"])
            except Exception:
                data = {}
    if not data:
        merged = dict(DEFAULT_SETTINGS)
    else:
        merged = {**DEFAULT_SETTINGS, **data}
        merged["text_model"] = {**DEFAULT_SETTINGS["text_model"], **data.get("text_model", {})}
        merged["vision_model"] = {**DEFAULT_SETTINGS["vision_model"], **data.get("vision_model", {})}
    if os.environ.get("DATA_ENTRY_FORCE_MOCK", "").strip().lower() in {"1", "true", "yes"}:
        merged["mock"] = True
    return merged


def save_model_settings(settings: dict) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('model', ?)",
            (json.dumps(settings, ensure_ascii=False),)
        )


# ===== 导入落库 =====

def commit_import(
    table_id: int,
    rows: list[dict],
    *,
    source_files: list[str] | None = None,
    skill_name: str = "",
    conflicts: list[dict] | None = None,
) -> dict:
    if not get_table(table_id):
        raise ValueError("结果表不存在")
    cleaned = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        data = {k: v for k, v in row.items() if k != "_conflicts"}
        if any(str(v).strip() for v in data.values() if v is not None):
            cleaned.append(data)
    if not cleaned:
        raise ValueError("没有可导入的数据")
    now = time.time()
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO import_batches (table_id, source_files, skill_name, row_count, conflicts, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                table_id,
                json.dumps(source_files or [], ensure_ascii=False),
                skill_name or "",
                len(cleaned),
                json.dumps(conflicts or [], ensure_ascii=False),
                now,
            ),
        )
        batch_id = cur.lastrowid
        for data in cleaned:
            conn.execute(
                "INSERT INTO imported_rows (table_id, batch_id, data, created_at) VALUES (?, ?, ?, ?)",
                (table_id, batch_id, json.dumps(data, ensure_ascii=False), now),
            )
    return {"batch_id": batch_id, "row_count": len(cleaned)}


def list_imported_rows(table_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, batch_id, data, created_at FROM imported_rows "
            "WHERE table_id = ? ORDER BY id",
            (table_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["data"] = json.loads(d["data"])
            except Exception:
                d["data"] = {}
            out.append(d)
        return out


def list_import_batches(table_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, source_files, skill_name, row_count, conflicts, created_at "
            "FROM import_batches WHERE table_id = ? ORDER BY id DESC",
            (table_id,),
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["batch_id"] = d.pop("id")
            try:
                d["source_files"] = json.loads(d["source_files"] or "[]")
            except Exception:
                d["source_files"] = []
            try:
                d["conflicts"] = json.loads(d["conflicts"] or "[]")
            except Exception:
                d["conflicts"] = []
            out.append(d)
        return out
