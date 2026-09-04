import unittest

from app.services.schema_extract import compose_schema_response, sanitize_columns, split_schema_reply


class SanitizeColumnsTest(unittest.TestCase):
    def test_drops_empty_and_duplicate_fields(self):
        cols = sanitize_columns([
            {"field": "cpds_id", "title": "ID", "type": "text", "required": True},
            {"field": "cpds_id", "title": "Dup", "type": "text"},
            {"field": "", "title": "No field"},
            {"field": "cl", "title": "", "type": "number"},
            {"field": "T1-2 hr", "title": "T1/2", "type": "weird"},
        ])
        fields = [c["field"] for c in cols]
        self.assertEqual(fields, ["cpds_id", "t1_2_hr"])
        self.assertEqual(cols[1]["type"], "text")
        self.assertEqual(cols[0]["required"], True)

    def test_keeps_select_options(self):
        cols = sanitize_columns([{
            "field": "species", "title": "种属", "type": "select",
            "options": ["human", "dog", ""],
        }])
        self.assertEqual(cols[0]["options"], ["human", "dog"])


class SplitSchemaReplyTest(unittest.TestCase):
    def test_splits_marker_block(self):
        raw = (
            "抽了 2 列，丢掉方法页。\n"
            "<<<SCHEMA>>>\n"
            '{"name":"Dog PK","description":"d","columns":['
            '{"field":"cpds_id","title":"ID","type":"text","required":true}],'
            '"skill_name":"PK skill","skill_md":"# PK"}\n'
            "<<<END>>>"
        )
        text, parsed = split_schema_reply(raw)
        self.assertIn("抽了 2 列", text)
        self.assertEqual(parsed["name"], "Dog PK")
        self.assertEqual(parsed["columns"][0]["field"], "cpds_id")

    def test_missing_block_returns_none(self):
        text, parsed = split_schema_reply("只是聊聊，没有结构")
        self.assertEqual(text, "只是聊聊，没有结构")
        self.assertIsNone(parsed)


class ComposeSchemaResponseTest(unittest.TestCase):
    def test_chat_does_not_replace_columns(self):
        draft = {
            "name": "Dog PK",
            "description": "old",
            "columns": [{"field": "cl", "title": "CL", "type": "number"}],
            "skill_name": "s",
            "skill_md": "# s",
        }
        out = compose_schema_response(
            "chat", "因为实体键要唯一",
            {"name": "X", "columns": [{"field": "x", "title": "X", "type": "text"}]},
            draft, "为什么要 cpds_id？",
        )
        self.assertEqual(out["intent"], "chat")
        self.assertEqual(out["columns"], [])
        self.assertEqual(out["name"], "Dog PK")

    def test_schema_keeps_existing_name_unless_asked(self):
        draft = {"name": "我的表", "description": "手改", "columns": [], "skill_name": "", "skill_md": ""}
        parsed = {
            "name": "Dog PK",
            "description": "ai desc",
            "columns": [{"field": "cl", "title": "CL", "type": "number"}],
            "skill_name": "PK",
            "skill_md": "# PK",
        }
        keep = compose_schema_response("schema", "ok", parsed, draft, "去掉 CLint")
        self.assertEqual(keep["name"], "我的表")
        self.assertEqual(keep["description"], "手改")
        self.assertEqual(keep["columns"][0]["field"], "cl")

        rename = compose_schema_response("schema", "ok", parsed, draft, "表名改成 Monkey PK")
        self.assertEqual(rename["name"], "Dog PK")

    def test_schema_zero_columns_does_not_wipe(self):
        draft = {"name": "A", "description": "", "columns": [{"field": "a", "title": "A"}], "skill_name": "", "skill_md": ""}
        out = compose_schema_response("schema", "没有结果列", {"name": "B", "columns": []}, draft, "")
        self.assertEqual(out["columns"], [])
        self.assertEqual(out["name"], "A")


if __name__ == "__main__":
    unittest.main()
