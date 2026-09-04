import unittest

from app.services.intent_router import (
    IntentDecision,
    api_intent,
    decide_action,
    merge_session_rules,
)


class MergeSessionRulesTest(unittest.TestCase):
    def test_append_and_dedupe(self):
        self.assertEqual(merge_session_rules("", "过滤对照"), "过滤对照")
        self.assertEqual(
            merge_session_rules("过滤对照", "小数两位"),
            "过滤对照\n小数两位",
        )
        self.assertEqual(merge_session_rules("过滤对照", "过滤对照"), "过滤对照")

    def test_clear(self):
        self.assertEqual(merge_session_rules("过滤对照", clear=True), "")


class DecideActionMockTest(unittest.TestCase):
    def test_empty_with_files_extract(self):
        d = decide_action("", has_files=True, has_rows=False)
        self.assertEqual(d.action, "extract")

    def test_analyze_with_files_empty_table_extract(self):
        d = decide_action(
            "希望快速分析，不要反复思考",
            has_files=True,
            has_rows=False,
        )
        self.assertEqual(d.action, "extract")
        self.assertIn("快速", d.rule_delta)

    def test_why_is_answer(self):
        d = decide_action("为啥HW1没有？", has_files=True, has_rows=True)
        self.assertEqual(d.action, "answer")

    def test_decimal_edit(self):
        d = decide_action(
            "小数位数超过2位的都要改成2位小数",
            has_files=True,
            has_rows=True,
        )
        self.assertEqual(d.action, "edit")

    def test_vague_with_rows_and_files_clarify(self):
        d = decide_action("这个看起来偏高", has_files=True, has_rows=True)
        self.assertEqual(d.action, "clarify")
        self.assertTrue(d.reply)

    def test_api_intent_map(self):
        self.assertEqual(api_intent("extract"), "recognize")
        self.assertEqual(api_intent("answer"), "chat")
        self.assertEqual(api_intent("clarify"), "chat")
        self.assertEqual(api_intent("edit"), "edit")


if __name__ == "__main__":
    unittest.main()
