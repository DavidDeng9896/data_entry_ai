import unittest

from app.services.schema_intent import classify_schema_intent, wants_meta_change


class SchemaIntentTest(unittest.TestCase):
    def test_empty_with_files_is_schema(self):
        self.assertEqual(classify_schema_intent("", has_files=True), "schema")
        self.assertEqual(classify_schema_intent("   ", has_files=True), "schema")

    def test_empty_without_files_is_chat(self):
        self.assertEqual(classify_schema_intent("", has_files=False), "chat")

    def test_describe_pk_columns_is_schema(self):
        text = "帮我建一张 Dog PK 表，只要 CL、Vss、AUC、T1/2、%F"
        self.assertEqual(classify_schema_intent(text, False), "schema")

    def test_remove_column_is_schema(self):
        self.assertEqual(classify_schema_intent("去掉 CLint", False), "schema")
        self.assertEqual(classify_schema_intent("T1/2 改成 number", False), "schema")

    def test_why_is_chat_even_with_files(self):
        self.assertEqual(classify_schema_intent("为什么要 cpds_id？", True), "chat")
        self.assertEqual(classify_schema_intent("这是什么意思", True), "chat")
        self.assertEqual(classify_schema_intent("解释一下为什么抽这列", True), "chat")

    def test_question_particle_without_schema_verb_is_chat(self):
        self.assertEqual(classify_schema_intent("这个 CL 看起来偏高吗", False), "chat")

    def test_wants_meta_change(self):
        self.assertTrue(wants_meta_change("表名改成 Monkey PK"))
        self.assertTrue(wants_meta_change("描述改成比格犬 PK 结果"))
        self.assertFalse(wants_meta_change("去掉 CLint"))


if __name__ == "__main__":
    unittest.main()
