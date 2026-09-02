import unittest

from app.schemas import ChatMessage, ColumnDef
from app.services.ai_service import _mock_chat_reply


COLS = [ColumnDef(field="cpds_id", title="ID")]


class MockChatIntentTest(unittest.TestCase):
    def test_chat_intent_does_not_extract(self):
        reply, rows = _mock_chat_reply(
            [ChatMessage(role="user", content="为啥截断")],
            COLS,
            "lots of file text",
            "skill",
            intent="chat",
            table_rows=[{"cpds_id": "HW1"}],
        )
        self.assertEqual(rows, [])
        self.assertIn("不抽数", reply)
        self.assertIn("HW1", reply)

    def test_recognize_intent_extracts_demo_rows(self):
        reply, rows = _mock_chat_reply(
            [ChatMessage(role="user", content="请识别")],
            COLS,
            "unrelated content",
            None,
            intent="recognize",
        )
        self.assertTrue(rows)
        self.assertIn("行", reply)
