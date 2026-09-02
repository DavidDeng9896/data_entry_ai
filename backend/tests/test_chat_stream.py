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
        self.assertIn("正在理解你的问题", body)
        self.assertIn("event: done", body)
        self.assertIn('"intent": "chat"', body)
