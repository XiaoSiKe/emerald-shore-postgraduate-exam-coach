import hashlib
import importlib.util
import tempfile
import unittest
import zipfile
from datetime import date, timedelta
from pathlib import Path

from qingan.materials import extract_questions, extract_text
from qingan.service import ingest, init
from qingan.state import read_json


def write_text_pdf(path, text):
    stream = f"BT /F1 12 Tf 72 100 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    payload = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(payload))
        payload.extend(f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(payload)


class ExtractionTests(unittest.TestCase):
    def test_text_html_and_questions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            text_file = root / "notes.txt"
            text_file.write_bytes("第一章\n第1题 什么是主要矛盾？\n说明理由。".encode("gb18030"))
            text, warnings = extract_text(text_file)
            self.assertIn("主要矛盾", text)
            self.assertEqual(warnings, [])
            questions = extract_questions(text, "source")
            self.assertEqual(len(questions), 1)
            self.assertEqual(questions[0]["locator"], "line:2")
            self.assertIsNone(questions[0]["answer"])

            html_file = root / "lesson.html"
            html_file.write_text("<h1>标题</h1><script>secret()</script><p>正文 &amp; 练习</p>", encoding="utf-8")
            html_text, _ = extract_text(html_file)
            self.assertIn("正文 & 练习", html_text)
            self.assertNotIn("secret", html_text)

    def test_minimal_docx_and_pptx(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            docx = root / "note.docx"
            with zipfile.ZipFile(docx, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    '<w:document xmlns:w="urn:w"><w:body><w:p><w:r><w:t>文档知识点</w:t></w:r></w:p></w:body></w:document>',
                )
            docx_text, _ = extract_text(docx)
            self.assertIn("文档知识点", docx_text)

            pptx = root / "slides.pptx"
            with zipfile.ZipFile(pptx, "w") as archive:
                archive.writestr(
                    "ppt/slides/slide1.xml",
                    '<p:sld xmlns:p="urn:p" xmlns:a="urn:a"><p:cSld><a:t>幻灯片重点</a:t></p:cSld></p:sld>',
                )
            pptx_text, _ = extract_text(pptx)
            self.assertIn("[Slide 1]", pptx_text)
            self.assertIn("幻灯片重点", pptx_text)

    def test_invalid_pdf_returns_recoverable_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "scan.pdf"
            path.write_bytes(b"%PDF-1.4\nnot-a-real-pdf")
            text, warnings = extract_text(path)
            self.assertEqual(text, "")
            self.assertTrue(warnings)

    @unittest.skipUnless(importlib.util.find_spec("pypdf"), "optional pypdf is not installed")
    def test_pdf_text_with_optional_parser(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "text.pdf"
            write_text_pdf(path, "Question 1 Retrieval practice evidence")
            text, warnings = extract_text(path)
            self.assertIn("Retrieval practice evidence", text)
            self.assertEqual(warnings, [])


class IngestTests(unittest.TestCase):
    def test_ingest_is_read_only_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = root / "study"
            init(str(workspace), (date.today() + timedelta(days=60)).isoformat(), 5, "目标")
            source = root / "真题.md"
            source.write_text("第1题 请解释概念。\n第2题 请完成计算。", encoding="utf-8")
            before = hashlib.sha256(source.read_bytes()).hexdigest()
            first = ingest(str(workspace), [str(source)], "past_paper")
            second = ingest(str(workspace), [str(source)], "past_paper")
            after = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(before, after)
            self.assertEqual(len(first["added_sources"]), 1)
            self.assertEqual(len(second["added_sources"]), 0)
            sources = read_json(workspace / ".qingan/sources.json")
            questions = read_json(workspace / ".qingan/question_bank.json")
            self.assertEqual(len(sources), 1)
            self.assertEqual(len(questions), 2)
            self.assertEqual(sources[0]["evidence_level"], "past_paper")


if __name__ == "__main__":
    unittest.main()
