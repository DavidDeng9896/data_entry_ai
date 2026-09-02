import os
import time
import unittest

os.environ["DATA_ENTRY_FORCE_MOCK"] = "1"

from fastapi.testclient import TestClient

from app.main import app
from app import database as db


class ImportPersistTest(unittest.TestCase):
    def setUp(self):
        os.environ["DATA_ENTRY_FORCE_MOCK"] = "1"
        self.client = TestClient(app)
        self.table_id = db.create_table(
            f"persist_test_{int(time.time()*1000)}_{id(self)}",
            "tmp",
            [{"field": "cpds_id", "title": "ID", "type": "text", "required": True, "options": [], "description": ""}],
        )["id"]

    def tearDown(self):
        db.delete_table(self.table_id)

    def test_commit_then_list_rows_and_history(self):
        res = self.client.post(
            f"/api/tables/{self.table_id}/imports",
            json={
                "rows": [{"cpds_id": "HW1"}, {"cpds_id": "HW2"}],
                "source_files": ["a.xlsx"],
                "skill_name": "demo",
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["row_count"], 2)
        self.assertTrue(data["batch_id"])

        listed = self.client.get(f"/api/tables/{self.table_id}/rows")
        self.assertEqual(listed.status_code, 200)
        rows = listed.json()
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["data"]["cpds_id"] for r in rows}, {"HW1", "HW2"})

        hist = self.client.get(f"/api/tables/{self.table_id}/imports")
        self.assertEqual(hist.status_code, 200)
        batches = hist.json()
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0]["row_count"], 2)
        self.assertIn("a.xlsx", batches[0]["source_files"])

        cards = self.client.get("/api/tables").json()
        card = next(t for t in cards if t["id"] == self.table_id)
        self.assertEqual(card["row_count"], 2)

    def test_empty_rows_rejected(self):
        res = self.client.post(
            f"/api/tables/{self.table_id}/imports",
            json={"rows": [], "source_files": []},
        )
        self.assertEqual(res.status_code, 400)
