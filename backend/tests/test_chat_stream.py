import os
import unittest

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
