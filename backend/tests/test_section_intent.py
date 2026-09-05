import unittest

from app.services.section_intent import (
    ask_user_where,
    classify_sections,
    content_for_extract,
    heuristic_role,
    pick_sections_by_user,
)
from app.services.section_model import Section


class SectionIntentTest(unittest.TestCase):
    def test_filename_is_not_result(self):
        self.assertEqual(heuristic_role("20210511 A375 CD73 ATP-GLO 汇总.xlsx"), "unknown")
        self.assertEqual(heuristic_role("Result sheet"), "result")
        self.assertEqual(heuristic_role("原始数据"), "process")

    def test_no_skill_picks_result_sheet_not_filename(self):
        secs = [
            Section("报告汇总.xlsx", "file", ""),
            Section("Result sheet", "sheet", "HW1 12"),
            Section("Raw Data", "sheet", "peak"),
        ]
        text, used, mode, tagged = content_for_extract(secs)
        self.assertEqual(mode, "result")
        self.assertIn("HW1", text)
        self.assertNotIn("peak", text)
        self.assertTrue(any(s.title == "Result sheet" for s in used))

    def test_ask_user_lists_sections_and_guess(self):
        secs = classify_sections([
            Section("x.xlsx", "file", ""),
            Section("Data", "sheet", "abc"),
            Section("方法", "sheet", "protocol"),
        ])
        msg = ask_user_where(secs)
        self.assertIn("Data", msg)
        self.assertIn("看", msg)
        self.assertIn("猜", msg)

    def test_user_picks_named_section(self):
        secs = [
            Section("Result sheet", "sheet", "HW1", role="result"),
            Section("Raw Data", "sheet", "peak", role="process"),
        ]
        picked = pick_sections_by_user("看 Result sheet", secs)
        self.assertEqual([s.title for s in picked], ["Result sheet"])

    def test_user_hint_overrides_result_mode(self):
        secs = [
            Section("报告.xlsx", "file", ""),
            Section("Result sheet", "sheet", "HW1"),
            Section("Raw Data", "sheet", "peak"),
        ]
        text, used, mode, _ = content_for_extract(secs, user_text="看 Raw Data")
        self.assertEqual(mode, "picked")
        self.assertEqual([s.title for s in used], ["Raw Data"])
        self.assertIn("peak", text)
        self.assertNotIn("HW1", text)

    def test_unknown_titles_fall_back_to_full(self):
        secs = [
            Section("Data", "sheet", "abc"),
            Section("Notes", "sheet", "xyz"),
        ]
        text, used, mode, _ = content_for_extract(secs)
        self.assertEqual(mode, "full")
        self.assertIn("abc", text)
        self.assertIn("xyz", text)

    def test_skill_policy_marks_named_pages(self):
        skill = "## 读取范围\n- 读取：`封面`、`PK 参数`\n- 跳过：`原始数据`\n"
        secs = [
            Section("封面", "sheet", "cover"),
            Section("原始数据", "sheet", "peak"),
            Section("PK参数", "sheet", "CL 1"),
        ]
        tagged = classify_sections(secs, skill_content=skill)
        roles = {s.title: s.role for s in tagged}
        self.assertEqual(roles["封面"], "result")
        self.assertEqual(roles["PK参数"], "result")
        self.assertEqual(roles["原始数据"], "process")


if __name__ == "__main__":
    unittest.main()
