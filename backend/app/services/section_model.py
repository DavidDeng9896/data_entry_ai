"""统一章节树：Excel sheet / PDF 页 / Word 标题。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SectionImage:
    name: str
    mime: str
    data: bytes = b""
    note: str = ""


@dataclass
class Section:
    title: str
    kind: str  # sheet | page | heading | file
    text: str = ""
    images: list[SectionImage] = field(default_factory=list)
    role: str = "unknown"  # result | process | unknown


def section_heading(sec: Section) -> str:
    if sec.kind == "sheet":
        return f"### Sheet: {sec.title}"
    if sec.kind == "page":
        return f"### 第 {sec.title} 页" if str(sec.title).isdigit() else f"### {sec.title}"
    if sec.kind == "file":
        return f"### 文件: {sec.title}"
    return f"### {sec.title}"


def render_sections(sections: list[Section], *, with_images_note: bool = True) -> str:
    parts = []
    for sec in sections:
        body = (sec.text or "").strip()
        extra = ""
        if with_images_note and sec.images:
            readable = sum(1 for im in sec.images if im.data and im.mime.startswith("image/"))
            unread = len(sec.images) - readable
            bits = [f"本节含 {len(sec.images)} 张图"]
            if readable:
                bits.append(f"{readable} 张可送视觉")
            if unread:
                bits.append(f"{unread} 张未能解码（{', '.join(im.note or im.mime for im in sec.images if not im.data)}）")
            extra = "\n" + "；".join(bits)
        if body or extra:
            parts.append(f"{section_heading(sec)}\n{body}{extra}".strip())
    return "\n\n".join(parts)


def catalog_lines(sections: list[Section]) -> list[str]:
    lines = []
    for i, sec in enumerate(sections, 1):
        if sec.kind == "file":
            continue
        tag = {"result": "像结果", "process": "像过程", "unknown": "不明"}.get(sec.role, "不明")
        nimg = f"，{len(sec.images)} 图" if sec.images else ""
        lines.append(f"{i}. {sec.title}（{sec.kind}，{tag}{nimg}）")
    return lines
