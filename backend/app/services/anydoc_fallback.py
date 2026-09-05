"""AnyDoc 兜底：主解析失败或正文为空时，转成统一章节树。"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from .section_model import Section

logger = logging.getLogger(__name__)

# 主路径未覆盖、但 AnyDoc 能吃的格式
ANYDOC_EXTRA_EXTS = {
    ".doc", ".docm", ".rtf",
    ".ppt", ".pptx", ".pptm", ".pps", ".ppsx",
    ".odt", ".ods", ".odp",
    ".epub", ".xlsb",
}

_HEADING = re.compile(r"^#{1,3}\s+(.+)$", re.M)


def anydoc_available() -> bool:
    try:
        import anydoc  # noqa: F401
        return True
    except Exception:
        return False


def anydoc_to_markdown(path: Path) -> str:
    import anydoc

    return anydoc.to_markdown(str(path))


def markdown_to_sections(md: str, *, file_label: str) -> list[Section]:
    """把 AnyDoc 的 Markdown 拆成章节；无标题则整份一章。"""
    text = (md or "").strip()
    head = Section(title=file_label, kind="file", text="")
    if not text:
        return [head]

    matches = list(_HEADING.finditer(text))
    if not matches:
        return [head, Section(title="正文", kind="heading", text=text)]

    out = [head]
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        kind = "heading"
        page_m = re.match(r"第\s*(\d+)\s*页$", title)
        if page_m:
            title = page_m.group(1)
            kind = "page"
        elif re.match(r"(?i)^sheet\s*:", title):
            title = re.sub(r"(?i)^sheet\s*:\s*", "", title).strip()
            kind = "sheet"
        out.append(Section(title=title or f"段{i+1}", kind=kind, text=body))
    return out


def sections_have_payload(sections: list[Section] | None) -> bool:
    if not sections:
        return False
    for sec in sections:
        if sec.kind == "file":
            continue
        if (sec.text or "").strip():
            return True
        if any(im.data and im.mime.startswith("image/") for im in sec.images):
            return True
    return False


def try_anydoc_sections(path: Path, *, file_label: str) -> list[Section] | None:
    """成功返回章节；不可用/失败返回 None。"""
    if not anydoc_available():
        return None
    try:
        md = anydoc_to_markdown(path)
    except Exception as exc:
        logger.info("AnyDoc 兜底失败 %s: %s", path.name, exc)
        return None
    if not (md or "").strip():
        return None
    return markdown_to_sections(md, file_label=file_label)
