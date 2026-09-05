"""统一解析入口 + AnyDoc 兜底 + 扫描页栅格。"""
from __future__ import annotations

import io
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from app.services import file_parser
from app.services.section_model import Section, SectionImage, render_sections
from app.services.section_parse import parse_to_sections, vision_images_to_send


_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _png_bytes(w=40, h=20, color=(240, 240, 240)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, format="PNG")
    return buf.getvalue()


def _image_only_pdf_bytes() -> bytes:
    """一页几乎无文字、只有位图的 PDF，模拟扫描件。"""
    import pypdfium2 as pdfium

    # pypdfium2 不擅长从零建 PDF；用 Pillow + 最小 PDF 手工包装太脆。
    # 这里用 img2pdf 思路：纯 Pillow 不行，改用 reportlab-free 的 pdfium 写入？
    # 最稳：用 pikepdf/reportlab。环境可能没有。用裸 PDF + 嵌入图像流。
    img = _png_bytes(80, 40)
    # 极简 PDF：一页贴一张 Image XObject（DeviceRGB 需要 raw；改用 JPEG）
    jpg = io.BytesIO()
    Image.new("RGB", (80, 40), (200, 200, 200)).save(jpg, format="JPEG", quality=90)
    jpg_bytes = jpg.getvalue()
    # Build a minimal one-page PDF with an embedded JPEG
    objects = []
    # 1: Catalog
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    # 2: Pages
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    # 3: Page
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 100] "
        b"/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>endobj\n"
    )
    # 4: Image
    objects.append(
        b"4 0 obj<< /Type /XObject /Subtype /Image /Width 80 /Height 40 "
        b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode "
        b"/Length " + str(len(jpg_bytes)).encode() + b" >>stream\n" + jpg_bytes + b"\nendstream endobj\n"
    )
    # 5: Content draws image
    content = b"q 200 0 0 100 0 0 cm /Im0 Do Q"
    objects.append(
        b"5 0 obj<< /Length " + str(len(content)).encode() + b" >>stream\n" + content + b"\nendstream endobj\n"
    )
    xref = []
    out = bytearray(b"%PDF-1.4\n")
    for obj in objects:
        xref.append(len(out))
        out.extend(obj)
    startxref = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in xref:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n".encode()
    )
    return bytes(out)


class ParseToTextUsesSectionsTest(unittest.TestCase):
    def test_parse_to_text_renders_sections_not_second_excel_pass(self):
        info = file_parser.save_upload("tiny.csv", b"a,b\n1,2\n")
        self.addCleanup(lambda: Path(info["path"]).unlink(missing_ok=True))
        secs = parse_to_sections(info["file_id"])
        expected = render_sections(secs)
        text = file_parser.parse_to_text(info["file_id"])
        self.assertEqual(text, expected)
        self.assertIn("1", text)

    def test_parse_to_text_truncates_after_render(self):
        info = file_parser.save_upload("big.txt", ("Z" * 5000).encode())
        self.addCleanup(lambda: Path(info["path"]).unlink(missing_ok=True))
        text = file_parser.parse_to_text(info["file_id"], max_chars=100)
        self.assertIn("已截断", text)
        self.assertTrue(len(text) < 200)


class RecognizeSingleParseTest(unittest.TestCase):
    def test_load_one_file_item_calls_sections_once(self):
        from app.routers import recognize
        import app.services.section_parse as sp

        info = file_parser.save_upload("tiny.csv", b"cpds_id,v\nA,1\n")
        self.addCleanup(lambda: Path(info["path"]).unlink(missing_ok=True))
        calls = {"n": 0}
        real = sp.parse_to_sections

        def wrapped(fid):
            calls["n"] += 1
            return real(fid)

        with mock.patch.object(sp, "parse_to_sections", side_effect=wrapped):
            with mock.patch.object(file_parser, "parse_to_text", side_effect=AssertionError("不应再走 parse_to_text")):
                item = recognize._load_one_file_item(info["file_id"], 0)
        self.assertEqual(calls["n"], 1)
        self.assertTrue(item.get("sections"))
        self.assertIn("A", item["text"])


class AnyDocFallbackTest(unittest.TestCase):
    def test_native_empty_pdf_uses_anydoc_markdown(self):
        from app.services import anydoc_fallback

        info = file_parser.save_upload("empty-like.pdf", _image_only_pdf_bytes())
        self.addCleanup(lambda: Path(info["path"]).unlink(missing_ok=True))

        fake_md = "### 第 1 页\n化合物 HW9 IC50 1.2\n"

        with mock.patch.object(anydoc_fallback, "anydoc_to_markdown", return_value=fake_md):
            # force native text empty by returning blank pages then fallback
            blank = [
                Section(title="empty.pdf", kind="file", text=""),
                Section(title="1", kind="page", text="", images=[]),
            ]
            with mock.patch("app.services.section_parse._pdf_sections", return_value=blank[1:]):
                with mock.patch("app.services.section_parse._enrich_empty_pdf_pages", side_effect=lambda p, s: s):
                    secs = parse_to_sections(info["file_id"])
        text = render_sections(secs)
        self.assertIn("HW9", text)
        self.assertIn("IC50", text)

    def test_unsupported_rtf_goes_anydoc(self):
        from app.services import anydoc_fallback

        info = file_parser.save_upload("note.rtf", b"{\\rtf1 HW42 result}")
        self.addCleanup(lambda: Path(info["path"]).unlink(missing_ok=True))
        with mock.patch.object(
            anydoc_fallback, "anydoc_to_markdown", return_value="### 正文\nHW42 result\n"
        ):
            secs = parse_to_sections(info["file_id"])
        self.assertTrue(any("HW42" in (s.text or "") for s in secs))


class ScannedPageVisionTest(unittest.TestCase):
    def test_empty_pdf_page_gets_raster_image(self):
        info = file_parser.save_upload("scan.pdf", _image_only_pdf_bytes())
        self.addCleanup(lambda: Path(info["path"]).unlink(missing_ok=True))
        secs = parse_to_sections(info["file_id"])
        pages = [s for s in secs if s.kind == "page"]
        self.assertTrue(pages)
        # 正文可能仍空，但应挂上可送视觉的栅格/内嵌图
        has_vision = any(
            im.data and im.mime.startswith("image/")
            for s in pages
            for im in s.images
        )
        self.assertTrue(has_vision)

    def test_full_mode_sends_empty_page_images(self):
        png = SectionImage("p.png", "image/png", data=_PNG)
        empty = Section("1", "page", "", [png], "unknown")
        texty = Section("2", "page", "protocol only", [], "process")
        sent = vision_images_to_send([empty, texty], "full")
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0].name, "p.png")

    def test_result_mode_only_sees_used_sections(self):
        """调用方只传入已选用的章；过程章不应出现在 used 里。"""
        png = SectionImage("p.png", "image/png", data=_PNG)
        result = Section("Result", "sheet", "HW", [png], "result")
        sent = vision_images_to_send([result], "result")
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0].name, "p.png")


if __name__ == "__main__":
    unittest.main()
