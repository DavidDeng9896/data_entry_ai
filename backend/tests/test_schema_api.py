import os
import unittest

os.environ["DATA_ENTRY_FORCE_MOCK"] = "1"

from fastapi.testclient import TestClient

from app.main import app
from app import database as db


class SchemaChatApiTest(unittest.TestCase):
    def setUp(self):
        os.environ["DATA_ENTRY_FORCE_MOCK"] = "1"
        self.client = TestClient(app)

    def test_chat_endpoint_returns_schema(self):
        res = self.client.post(
            "/api/tables/schema/chat",
            json={
                "messages": [{"role": "user", "content": "帮我建一张 Dog PK 表，只要 CL、Vss、AUC"}],
                "file_ids": [],
                "name": "",
                "description": "",
                "columns": [],
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["intent"], "schema")
        self.assertTrue(data["columns"])
        self.assertTrue(data["skill_md"])

    def test_stream_emits_done_intent(self):
        with self.client.stream(
            "POST",
            "/api/tables/schema/chat/stream",
            json={
                "messages": [{"role": "user", "content": "为什么要 cpds_id？"}],
                "file_ids": [],
                "name": "Dog PK",
                "columns": [{"field": "cl", "title": "CL", "type": "number"}],
            },
        ) as res:
            self.assertEqual(res.status_code, 200)
            body = "".join(res.iter_text())
        self.assertIn("已连接，开始处理", body)
        self.assertIn("正在理解你的问题", body)
        self.assertIn("event: done", body)
        self.assertIn('"intent": "chat"', body)

    def test_stream_file_emits_parse_step(self):
        up = self.client.post(
            "/api/recognize/upload",
            files={"file": ("tiny.csv", b"id,cl\nA,1\n", "text/csv")},
        )
        self.assertEqual(up.status_code, 200)
        fid = up.json()["file_id"]
        with self.client.stream(
            "POST",
            "/api/tables/schema/chat/stream",
            json={
                "messages": [{"role": "user", "content": "抽出列"}],
                "file_ids": [fid],
                "name": "",
                "columns": [],
            },
        ) as res:
            self.assertEqual(res.status_code, 200)
            body = "".join(res.iter_text())
        self.assertIn("正在解析附件", body)
        self.assertIn("event: done", body)
        self.assertIn('"intent": "schema"', body)

    def test_create_table_then_skill_not_enabled(self):
        name = "schema_api_dog_pk"
        for t in db.list_tables():
            if t["name"] == name:
                db.delete_table(t["id"])
        created = self.client.post(
            "/api/tables",
            json={
                "name": name,
                "description": "from schema test",
                "columns": [
                    {"field": "cpds_id", "title": "ID", "type": "text", "required": True},
                    {"field": "cl", "title": "CL", "type": "number"},
                ],
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        table_id = created.json()["id"]
        sk = self.client.post(
            "/api/skills",
            json={"name": "PK · schema test", "content": "# PK\n\n## 字段映射\n"},
        )
        self.assertEqual(sk.status_code, 200, sk.text)
        skill_id = sk.json()["id"]
        detail = self.client.get(f"/api/skills/{skill_id}").json()
        self.assertFalse(detail.get("enabled"))
        db.delete_table(table_id)
        self.client.delete(f"/api/skills/{skill_id}")
