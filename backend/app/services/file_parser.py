"""文件解析：把上传的非标准文件解析成『文本 + 表格』，供 LLM 结构化。
- Excel/CSV：pandas 读出所有 sheet，转 markdown 表格文本
- PDF：pdfplumber 提取文本和表格
- 图片：返回 bytes，走视觉模型
"""
import io
import uuid
from pathlib import Path

import pandas as pd
import pdfplumber

from ..config import DATA_DIR

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}
EXCEL_EXTS = {".xlsx", ".xls", ".xlsm", ".csv", ".tsv"}


def save_upload(filename: str, content: bytes) -> dict:
    """保存上传文件，返回 {file_id, filename, ext, path}"""
    ext = Path(filename).suffix.lower()
    file_id = uuid.uuid4().hex[:12]
    safe_name = f"{file_id}{ext}"
    path = UPLOAD_DIR / safe_name
    path.write_bytes(content)
    return {"file_id": file_id, "filename": filename, "ext": ext, "path": str(path)}


def _get_path(file_id: str) -> Path:
    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matches:
        raise FileNotFoundError(f"file_id {file_id} 不存在")
    return matches[0]


def is_image(file_id: str) -> bool:
    return _get_path(file_id).suffix.lower() in IMAGE_EXTS


def get_image_bytes(file_id: str) -> tuple[bytes, str]:
    path = _get_path(file_id)
    return path.read_bytes(), path.suffix.lower().lstrip(".")


def parse_to_text(file_id: str, max_chars: int = 20000) -> str:
    """把文件内容解析成文本（markdown 表格优先），截断到 max_chars"""
    path = _get_path(file_id)
    ext = path.suffix.lower()

    if ext in EXCEL_EXTS:
        text = _parse_excel(path)
    elif ext == ".pdf":
        text = _parse_pdf(path)
    elif ext in {".txt", ".md", ".json"}:
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"不支持的文件类型: {ext}（扫描件/图片请走视觉模型）")

    if len(text) > max_chars:
        text = text[:max_chars] + f"\n...(已截断，共 {len(text)} 字符)"
    return text


def _df_to_markdown(df: pd.DataFrame) -> str:
    """DataFrame 转 markdown 表格，列名不清时保留原始内容"""
    df = df.dropna(how="all").dropna(axis=1, how="all")
    if df.empty:
        return ""
    df = df.fillna("")
    df.columns = [str(c) if str(c) and not str(c).startswith("Unnamed") else f"col{i}" for i, c in enumerate(df.columns)]
    return df.to_markdown(index=False)


def _parse_excel(path: Path) -> str:
    ext = path.suffix.lower()
    parts = []
    if ext in {".csv", ".tsv"}:
        sep = "\t" if ext == ".tsv" else None
        df = pd.read_csv(path, sep=sep, engine="python", dtype=str, header=None)
        parts.append(_df_to_markdown(df))
    else:
        sheets = pd.read_excel(path, sheet_name=None, dtype=str, header=None)
        for name, df in sheets.items():
            md = _df_to_markdown(df)
            if md:
                parts.append(f"### Sheet: {name}\n{md}")
    return "\n\n".join(p for p in parts if p)


def _parse_pdf(path: Path) -> str:
    parts = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if text.strip():
                parts.append(f"### 第 {i+1} 页\n{text}")
            for t_idx, table in enumerate(page.extract_tables()):
                df = pd.DataFrame(table)
                md = _df_to_markdown(df)
                if md:
                    parts.append(f"### 第 {i+1} 页 表格 {t_idx+1}\n{md}")
    return "\n\n".join(parts)
