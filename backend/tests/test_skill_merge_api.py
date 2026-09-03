import os
import unittest

os.environ["DATA_ENTRY_FORCE_MOCK"] = "1"

from fastapi.testclient import TestClient

from app.main import app
from app import database as db


class SkillMergeApiTest(unittest.TestCase):
    def setUp(self):
        os.environ["DATA_ENTRY_FORCE_MOCK"] = "1"
        self.client = TestClient(app)
        self.skill_id = db.save_skill(
            None,
            "merge_base_test",
            "# Base\n\n## 匹配线索\n- old\n\n## 字段映射\n| a | b |\n",
        )

    def tearDown(self):
        db.delete_skill(self.skill_id)

    def test_merge_updates_existing_skill(self):
        res = self.client.post(
            "/api/skills/merge",
            json={
                "target_id": self.skill_id,
                "draft_md": "# Draft\n\n## 匹配线索\n- new\n\n## 字段映射\n| c | d |\n",
                "name": "merge_base_test",
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertTrue(data["ok"])
        detail = self.client.get(f"/api/skills/{self.skill_id}").json()
        self.assertIn("old", detail["content"])
        self.assertIn("new", detail["content"])
        self.assertFalse(detail["enabled"])
