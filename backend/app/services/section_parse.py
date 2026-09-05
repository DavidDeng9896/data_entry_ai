"""把各类文件切成统一章节，并挂上该章的嵌入图。"""
from __future__ import annotations

import re
from pathlib import Path
from posixpath import join as posix_join
from posixpath import normpath
from zipfile import ZipFile

from .file_parser import (
    EXCEL_EXTS,
    IMAGE_EXTS,
    _df_to_markdown,
    _get_path,
    _parse_excel,
    _read_excel_displayed,
    _read_excel_sheets,
    original_filename,
    spreadsheet_reject_reason,
)
from .section_model import Section, SectionImage

_VISION_OK = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
_SKIP_REL_EXTS = {".xml", ".vml", ".rels"}


def parse_to_sections(file_id: str) -> list[Section]:
    path = _get_path(file_id)
    ext = path.suffix.lower()
    label = original_filename(file_id)
    head = Section(title=label, kind="file", text="")

    from .anydoc_fallback import (
        ANYDOC_EXTRA_EXTS,
        sections_have_payload,
        try_anydoc_sections,
    )

    try:
        if ext in EXCEL_EXTS and ext not in {".csv", ".tsv"}:
            sections = [head] + _excel_sections(path)
        elif ext in {".csv", ".tsv"}:
            sections = [head, Section(title=label, kind="sheet", text=_parse_excel(path))]
        elif ext == ".pdf":
            sections = [head] + _enrich_empty_pdf_pages(path, _pdf_sections(path))
        elif ext in {".docx"}:
            sections = [head] + _docx_sections(path)
        elif ext in IMAGE_EXTS:
            data = path.read_bytes()
            mime = "image/jpeg" if ext in {".jpg", ".jpeg"} else f"image/{ext.lstrip('.')}"
            sections = [head, Section(
                title=label, kind="heading", text="（整份为图片）",
                images=[SectionImage(name=label, mime=mime, data=data)],
            )]
        elif ext in {".txt", ".md", ".json"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            if not text:
                raise ValueError(f"空文件: {ext}")
            sections = [head, Section(title=label, kind="heading", text=text)]
        elif ext in ANYDOC_EXTRA_EXTS:
            sections = None
        else:
            raise ValueError(f"不支持的文件类型: {ext}")
    except Exception as native_err:
        fallback = try_anydoc_sections(path, file_label=label)
        if fallback and sections_have_payload(fallback):
            return fallback
        raise native_err

    if sections is None or not sections_have_payload(sections):
        fallback = try_anydoc_sections(path, file_label=label)
        if fallback and sections_have_payload(fallback):
            return fallback
        if sections is None:
            raise ValueError(f"不支持的文件类型: {ext}")
    return sections


def _nearly_empty_text(text: str) -> bool:
    return len((text or "").strip()) < 40


def _page_has_vision_image(sec: Section) -> bool:
    return any(im.data and im.mime.startswith("image/") for im in sec.images)


def _rasterize_pdf_page(path: Path, page_no: int, scale: float = 2.0) -> SectionImage | None:
    """把 PDF 第 page_no 页（1-based）栅格成 PNG，供扫描页送视觉。"""
    try:
        import pypdfium2 as pdfium
    except Exception:
        return None
    try:
        doc = pdfium.PdfDocument(str(path))
    except Exception:
        return None
    try:
        if page_no < 1 or page_no > len(doc):
            return None
        page = doc[page_no - 1]
        bitmap = page.render(scale=scale)
        pil = bitmap.to_pil()
        import io
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        return SectionImage(
            name=f"page{page_no}-raster.png",
            mime="image/png",
            data=buf.getvalue(),
            note="扫描/空页栅格",
        )
    except Exception:
        return None
    finally:
        try:
            doc.close()
        except Exception:
            pass


def _enrich_empty_pdf_pages(path: Path, pages: list[Section]) -> list[Section]:
    """正文几乎为空的页：若无可送视觉的图，则栅格化整页挂上。"""
    out = []
    for sec in pages:
        if sec.kind != "page" or not _nearly_empty_text(sec.text) or _page_has_vision_image(sec):
            out.append(sec)
            continue
        try:
            page_no = int(str(sec.title))
        except ValueError:
            out.append(sec)
            continue
        raster = _rasterize_pdf_page(path, page_no)
        if raster is None:
            out.append(sec)
            continue
        images = list(sec.images) + [raster]
        out.append(Section(sec.title, sec.kind, sec.text, images, sec.role))
    return out


def _excel_sections(path: Path) -> list[Section]:
    reason = spreadsheet_reject_reason(path.name, path.read_bytes())
    if reason:
        raise ValueError(reason)
    try:
        sheets = _read_excel_displayed(path)
    except Exception:
        sheets = _read_excel_sheets(path)
    images = _xlsx_images_by_sheet(path)
    out = []
    for name, df in sheets.items():
        md = _df_to_markdown(df)
        out.append(Section(title=str(name), kind="sheet", text=md, images=images.get(str(name), [])))
    return out


def _zip_resolve(rels_path: str, target: str) -> str:
    target = (target or "").replace("\\", "/").split("#")[0]
    if target.startswith("/"):
        return target.lstrip("/")
    base_dir = rels_path.rsplit("/", 1)[0]
    return normpath(posix_join(base_dir, target))


def _rels_path_for(part: str) -> str:
    folder, name = part.rsplit("/", 1) if "/" in part else ("", part)
    return f"{folder}/_rels/{name}.rels" if folder else f"_rels/{name}.rels"


def _image_from_zip_part(zf: ZipFile, part: str) -> SectionImage:
    fname = part.split("/")[-1]
    ext = Path(fname).suffix.lower()
    if ext in _VISION_OK:
        mime = "image/jpeg" if ext in {".jpg", ".jpeg"} else f"image/{ext.lstrip('.')}"
        return SectionImage(name=fname, mime=mime, data=zf.read(part))
    return SectionImage(
        name=fname,
        mime="application/octet-stream",
        note=f"{ext or 'bin'} 暂无法解码",
    )


def _collect_media_from_rels(
    zf: ZipFile, names: set[str], rels_path: str, bucket: list[SectionImage], seen: set[str],
) -> None:
    if rels_path not in names:
        return
    xml = zf.read(rels_path).decode("utf-8", "replace")
    for target in re.findall(r'Target="([^"]+)"', xml):
        part = _zip_resolve(rels_path, target)
        if part not in names:
            fname = target.replace("\\", "/").split("/")[-1]
            part = next(
                (c for c in (f"xl/media/{fname}", f"xl/embeddings/{fname}") if c in names),
                "",
            )
        if not part or part in seen:
            continue
        ext = Path(part).suffix.lower()
        if ext in _SKIP_REL_EXTS:
            _collect_media_from_rels(zf, names, _rels_path_for(part), bucket, seen)
            continue
        seen.add(part)
        bucket.append(_image_from_zip_part(zf, part))


def _xlsx_images_by_sheet(path: Path) -> dict[str, list[SectionImage]]:
    mapped: dict[str, list[SectionImage]] = {}
    try:
        zf = ZipFile(path)
    except Exception:
        return mapped
    try:
        names = set(zf.namelist())
        sheet_files = _xlsx_sheet_targets(zf)
        for sheet_name, sheet_xml in sheet_files.items():
            rels = _rels_path_for(sheet_xml)
            if rels not in names:
                rels = f"xl/worksheets/_rels/{Path(sheet_xml).name}.rels"
            bucket: list[SectionImage] = []
            _collect_media_from_rels(zf, names, rels, bucket, set())
            if bucket:
                mapped[sheet_name] = bucket
    except Exception:
        return mapped
    finally:
        zf.close()
    return mapped


def _xlsx_sheet_targets(zf: ZipFile) -> dict[str, str]:
    wb = zf.read("xl/workbook.xml").decode("utf-8", "replace")
    rels = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8", "replace")
    rid_to_target = {}
    for rid, target in re.findall(r'Id="(rId\d+)"[^>]*Target="([^"]+)"', rels):
        rid_to_target[rid] = target
    if not rid_to_target:
        for target, rid in re.findall(r'Target="([^"]+)"[^>]*Id="(rId\d+)"', rels):
            rid_to_target[rid] = target
    pairs = re.findall(r'<sheet\b[^>]*\bname="([^"]+)"[^>]*\br:id="(rId\d+)"', wb)
    if not pairs:
        pairs = [
            (name, rid)
            for rid, name in re.findall(r'<sheet\b[^>]*\br:id="(rId\d+)"[^>]*\bname="([^"]+)"', wb)
        ]
    out = {}
    for name, rid in pairs:
        target = rid_to_target.get(rid, "")
        if not target:
            continue
        if not target.startswith("xl/"):
            target = "xl/" + target.replace("../", "").lstrip("/")
        out[name] = target
    return out


def _pdf_sections(path: Path) -> list[Section]:
    import pdfplumber

    out = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            tables = []
            for t_idx, table in enumerate(page.extract_tables() or []):
                import pandas as pd
                from .file_parser import _df_to_markdown
                md = _df_to_markdown(pd.DataFrame(table))
                if md:
                    tables.append(f"表格 {t_idx + 1}\n{md}")
            body = "\n\n".join(p for p in (text, *tables) if p.strip())
            images = _pdf_page_images(page, i)
            out.append(Section(title=str(i), kind="page", text=body, images=images))
    return out


def _pdf_page_images(page, page_no: int) -> list[SectionImage]:
    out: list[SectionImage] = []
    try:
        infos = getattr(page, "images", None) or []
    except Exception:
        return out
    for j, info in enumerate(infos, 1):
        data = b""
        if isinstance(info, dict) and info.get("stream") is not None:
            try:
                data = info["stream"].get_data()
            except Exception:
                data = b""
        if data[:3] == b"\xff\xd8\xff":
            out.append(SectionImage(name=f"page{page_no}-img{j}", mime="image/jpeg", data=data))
        elif data[:8] == b"\x89PNG\r\n\x1a\n":
            out.append(SectionImage(name=f"page{page_no}-img{j}", mime="image/png", data=data))
        else:
            out.append(SectionImage(
                name=f"page{page_no}-img{j}",
                mime="application/octet-stream",
                note="PDF 内嵌图未能解码",
            ))
    return out


def _image_from_rel(rel) -> SectionImage | None:
    try:
        blob = rel.target_part.blob
        name = Path(rel.target_ref).name
    except Exception:
        return None
    ext = Path(name).suffix.lower()
    if ext in _VISION_OK:
        mime = "image/jpeg" if ext in {".jpg", ".jpeg"} else f"image/{ext.lstrip('.')}"
        return SectionImage(name=name, mime=mime, data=blob)
    return SectionImage(name=name, mime="application/octet-stream", note=f"{ext} 暂无法解码")


def _docx_sections(path: Path) -> list[Section]:
    from docx import Document
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph

    doc = Document(str(path))
    image_rels = {}
    try:
        for rid, rel in doc.part.rels.items():
            if "image" in (getattr(rel, "reltype", "") or ""):
                image_rels[rid] = rel
    except Exception:
        image_rels = {}

    sections: list[Section] = []
    current = Section(title="正文", kind="heading", text="")
    blobs: list[str] = []

    def flush():
        nonlocal current, blobs
        current.text = "\n".join(blobs).strip()
        if current.text or current.images:
            sections.append(current)

    def attach_images(element):
        for blip in element.iter():
            if not str(blip.tag).endswith("}blip"):
                continue
            rid = blip.get(qn("r:embed"))
            rel = image_rels.get(rid)
            if rel is None:
                continue
            im = _image_from_rel(rel)
            if im:
                current.images.append(im)

    for child in doc.element.body:
        tag = child.tag.split("}")[-1]
        if tag == "p":
            p = Paragraph(child, doc)
            style = (p.style.name if p.style is not None else "") or ""
            if style.startswith("Heading"):
                flush()
                current = Section(title=p.text.strip() or style, kind="heading", text="")
                blobs = []
                attach_images(child)
                continue
            if p.text.strip():
                blobs.append(p.text.strip())
            attach_images(child)
        elif tag == "tbl":
            rows = []
            for row in child.iter(qn("w:tr")):
                cells = [
                    "".join(t.text or "" for t in c.iter(qn("w:t")))
                    for c in row.findall(qn("w:tc"))
                ]
                if any(x.strip() for x in cells):
                    rows.append(" | ".join(cells))
            if rows:
                blobs.append("\n".join(rows))
            attach_images(child)
    flush()
    return sections or [Section(title="正文", kind="heading", text="")]


def images_for_vision(sections: list[Section]) -> list[SectionImage]:
    """给定章节里可送视觉的图（调用方只传入结果区 / 用户点名的章）。"""
    out = []
    for sec in sections:
        for im in sec.images:
            if im.data and im.mime.startswith("image/"):
                out.append(im)
    return out


def _image_only_section(sec: Section) -> bool:
    body = (sec.text or "").strip()
    return bool(sec.images) and (not body or body == "（整份为图片）")


def _empty_page_with_images(sec: Section) -> bool:
    """仅 PDF 空页/扫描页：全文模式下补送视觉。短正文的 sheet 不算。"""
    if sec.kind != "page":
        return False
    if not any(im.data and im.mime.startswith("image/") for im in sec.images):
        return False
    return _nearly_empty_text(sec.text)


def vision_images_to_send(used: list[Section], mode: str) -> list[SectionImage]:
    """结果区或用户点名的章才送图；全文时只补空页/纯图章，不倾销过程图。"""
    content = [s for s in used if s.kind != "file"]
    if mode in ("result", "picked"):
        return images_for_vision(content)
    if content and all(_image_only_section(s) for s in content):
        return images_for_vision(content)
    empty_img = [s for s in content if _empty_page_with_images(s) or _image_only_section(s)]
    if empty_img:
        return images_for_vision(empty_img)
    return []
