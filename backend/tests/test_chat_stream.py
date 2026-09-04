import os
import unittest
from pathlib import Path

os.environ["DATA_ENTRY_FORCE_MOCK"] = "1"

from fastapi.testclient import TestClient

from app.main import app


class ChatStreamApiTest(unittest.TestCase):
    def test_stream_chat_intent_has_question_step(self):
        client = TestClient(app)
        with client.stream(
            "POST",
            "/api/recognize/chat/stream",
            json={
                "messages": [{"role": "user", "content": "为啥截断"}],
                "columns": [{"field": "cpds_id", "title": "ID", "type": "text"}],
                "file_ids": [],
                "auto_skill": True,
            },
        ) as res:
            self.assertEqual(res.status_code, 200)
            body = "".join(res.iter_text())
        self.assertIn("已连接，开始处理", body)
        self.assertIn("正在理解你的问题", body)
        self.assertIn("event: done", body)
        self.assertIn('"intent": "chat"', body)

    def test_stream_file_emits_parse_progress(self):
        client = TestClient(app)
        up = client.post(
            "/api/recognize/upload",
            files={"file": ("tiny.csv", b"cpds_id,v\nA,1\n", "text/csv")},
        )
        self.assertEqual(up.status_code, 200)
        fid = up.json()["file_id"]
        with client.stream(
            "POST",
            "/api/recognize/chat/stream",
            json={
                "messages": [{"role": "user", "content": "请识别"}],
                "columns": [{"field": "cpds_id", "title": "ID", "type": "text"}],
                "file_ids": [fid],
                "auto_skill": True,
            },
        ) as res:
            self.assertEqual(res.status_code, 200)
            body = "".join(res.iter_text())
        self.assertIn("已连接，开始处理", body)
        self.assertIn("正在解析附件 1/1：tiny.csv", body)
        self.assertIn("正在匹配 Skill", body)
        self.assertIn("event: done", body)

    def test_stream_why_missing_does_not_parse_files(self):
        client = TestClient(app)
        up = client.post(
            "/api/recognize/upload",
            files={"file": ("tiny.csv", b"cpds_id,v\nA,1\n", "text/csv")},
        )
        fid = up.json()["file_id"]
        with client.stream(
            "POST",
            "/api/recognize/chat/stream",
            json={
                "messages": [{"role": "user", "content": "为啥HW350003A化合物数据没有？"}],
                "columns": [
                    {"field": "cpds_id", "title": "ID", "type": "text"},
                    {"field": "cl", "title": "CL", "type": "number"},
                ],
                "file_ids": [fid],
                "auto_skill": True,
                "rows": [{"cpds_id": "HW1", "cl": "0.20"}],
            },
        ) as res:
            self.assertEqual(res.status_code, 200)
            body = "".join(res.iter_text())
        self.assertIn("正在理解你的问题", body)
        self.assertNotIn("正在解析附件", body)
        self.assertNotIn("正在匹配 Skill", body)
        self.assertNotIn("正在读取", body)
        self.assertIn('"intent": "chat"', body)
        self.assertIn("HW1", body)
        self.assertIn("不抽数", body)

    def test_stream_decimal_edit_does_not_reimport(self):
        client = TestClient(app)
        up = client.post(
            "/api/recognize/upload",
            files={"file": ("tiny.csv", b"cpds_id,v\nA,1\n", "text/csv")},
        )
        fid = up.json()["file_id"]
        with client.stream(
            "POST",
            "/api/recognize/chat/stream",
            json={
                "messages": [{"role": "user", "content": "小数位数超过2位的都要改成2位小数"}],
                "columns": [
                    {"field": "cpds_id", "title": "ID", "type": "text"},
                    {"field": "cl", "title": "CL", "type": "number"},
                ],
                "file_ids": [fid],
                "auto_skill": True,
                "rows": [
                    {"cpds_id": "HW1", "cl": "0.2046234"},
                    {"cpds_id": "HW2", "cl": "1.2"},
                ],
            },
        ) as res:
            self.assertEqual(res.status_code, 200)
            body = "".join(res.iter_text())
        self.assertIn("正在按你的要求改已填格子", body)
        self.assertNotIn("正在解析附件", body)
        self.assertNotIn("正在匹配 Skill", body)
        self.assertIn('"intent": "edit"', body)
        self.assertIn("0.20", body)
        self.assertIn("没有重新识别", body)
        self.assertNotIn("CHO01", body)

    def test_stream_analyze_with_empty_table_parses_files(self):
        client = TestClient(app)
        up = client.post(
            "/api/recognize/upload",
            files={"file": ("tiny.csv", b"cpds_id,v\nA,1\n", "text/csv")},
        )
        self.assertEqual(up.status_code, 200)
        fid = up.json()["file_id"]
        with client.stream(
            "POST",
            "/api/recognize/chat/stream",
            json={
                "messages": [{"role": "user", "content": "希望快速分析，不要反复思考"}],
                "columns": [{"field": "cpds_id", "title": "ID", "type": "text"}],
                "file_ids": [fid],
                "auto_skill": True,
                "rows": [],
            },
        ) as res:
            self.assertEqual(res.status_code, 200)
            body = "".join(res.iter_text())
        self.assertIn("正在解析附件", body)
        self.assertIn("event: done", body)
        self.assertIn('"intent": "recognize"', body)
        self.assertNotIn("正在理解你的问题", body)
        self.assertNotIn("没有收到附件", body)

    def test_stream_skips_fake_xlsx_and_keeps_good_file(self):
        from app.services import file_parser

        client = TestClient(app)
        up = client.post(
            "/api/recognize/upload",
            files={"file": ("tiny.csv", b"cpds_id,v\nA,1\n", "text/csv")},
        )
        self.assertEqual(up.status_code, 200)
        good_id = up.json()["file_id"]
        bad = file_parser.save_upload("enc.xlsx", b"%TSD-Header-###%\x00not-excel")
        self.addCleanup(lambda: Path(bad["path"]).unlink(missing_ok=True))
        with client.stream(
            "POST",
            "/api/recognize/chat/stream",
            json={
                "messages": [{"role": "user", "content": "请识别"}],
                "columns": [{"field": "cpds_id", "title": "ID", "type": "text"}],
                "file_ids": [good_id, bad["file_id"]],
                "auto_skill": True,
            },
        ) as res:
            self.assertEqual(res.status_code, 200)
            body = "".join(res.iter_text())
        self.assertIn("event: done", body)
        self.assertNotIn("event: error", body)
        self.assertIn("已跳过", body)
        self.assertIn("enc.xlsx", body)
        self.assertNotIn("File is not a zip file", body)
