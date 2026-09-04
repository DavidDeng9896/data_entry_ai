import os
import unittest
from unittest.mock import patch

os.environ["DATA_ENTRY_FORCE_MOCK"] = "1"

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import ColumnDef
from app.services.ai_service import _build_system_prompt

GROUPS = ["control 1", "control 2", "0.4 μM", "2 μM", "10 μM", "washout", "Dofetilide"]
ROWS = [{"cpds_id": "HW181125", "treatment_group": g} for g in GROUPS]


class DefaultNoMergeTest(unittest.TestCase):
    def test_prompt_defers_row_grain_to_skill(self):
        text = _build_system_prompt(
            [ColumnDef(field="cpds_id", title="ID")],
            "同一化合物每个处理组一行，不要合并。",
        )
        self.assertIn("行数与切分以 Skill 为准", text)
        self.assertIn("同一化合物每个处理组一行", text)

    def test_chat_json_keeps_all_rows_with_same_cpds_id(self):
        client = TestClient(app)
        with patch("app.routers.recognize.ai_service.chat", return_value=("抽出 7 行", ROWS)):
            res = client.post(
                "/api/recognize/chat",
                json={
                    "messages": [{"role": "user", "content": "请识别"}],
                    "columns": [
                        {"field": "cpds_id", "title": "ID", "type": "text"},
                        {"field": "treatment_group", "title": "Group", "type": "text"},
                    ],
                    "file_ids": [],
                    "auto_skill": False,
                },
            )
        self.assertEqual(res.status_code, 200)
        rows = res.json()["rows"]
        self.assertEqual(len(rows), 7)
        self.assertEqual([r["treatment_group"] for r in rows], GROUPS)
