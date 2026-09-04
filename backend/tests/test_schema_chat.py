import unittest

from app.schemas import ChatMessage, ColumnDef
from app.services.schema_chat import run_schema_chat


class SchemaChatMockTest(unittest.TestCase):
    def test_describe_pk_returns_internal_columns(self):
        out = run_schema_chat(
            messages=[ChatMessage(role="user", content="帮我建一张 Dog PK 表，只要 CL、Vss、AUC、T1/2、%F")],
            file_ids=[],
            name="",
            description="",
            columns=[],
            skill_name="",
            skill_md="",
        )
        self.assertEqual(out["intent"], "schema")
        fields = [c["field"] for c in out["columns"]]
        self.assertIn("cpds_id", fields)
        self.assertTrue(any("cl" in f for f in fields))
        self.assertTrue(out["skill_md"])
        self.assertIn("字段映射", out["skill_md"])
        self.assertTrue(out["name"])

    def test_why_question_does_not_replace_columns(self):
        existing = [ColumnDef(field="cl", title="CL", type="number")]
        out = run_schema_chat(
            messages=[ChatMessage(role="user", content="为什么要 cpds_id？")],
            file_ids=[],
            name="Dog PK",
            description="old",
            columns=existing,
            skill_name="s",
            skill_md="# s",
        )
        self.assertEqual(out["intent"], "chat")
        self.assertEqual(out["columns"], [])
        self.assertEqual(out["name"], "Dog PK")
        self.assertIn("问答", out["reply"])

    def test_keeps_hand_edited_name(self):
        out = run_schema_chat(
            messages=[ChatMessage(role="user", content="去掉 CLint")],
            file_ids=[],
            name="我的表",
            description="手改描述",
            columns=[],
            skill_name="",
            skill_md="",
        )
        self.assertEqual(out["intent"], "schema")
        self.assertEqual(out["name"], "我的表")
        self.assertEqual(out["description"], "手改描述")
        self.assertTrue(out["columns"])
