import unittest
from pathlib import Path

from app.services.sheet_focus import focus_content_for_model, parse_sheet_policy

PK_SKILL = Path("/workspace/doc/skills/pk-precent-winnonlin.md").read_text(encoding="utf-8")

SYNTH = "\n".join([
    "### Sheet: 封面",
    "普瑞昇",
    "### Sheet: 结果汇总",
    "时程浓度",
    "### Sheet: PK参数",
    "Cl_obs 0.70",
    "### Sheet: 原始数据",
    "peak area",
    "### Sheet: 试验设计",
    "SD 大鼠",
])


class SheetFocusTest(unittest.TestCase):
    def test_pk_skill_declares_read_range(self):
        policy = parse_sheet_policy(PK_SKILL)
        self.assertIsNotNone(policy)
        self.assertTrue(any("pk参数" in t.replace(" ", "").lower() for t in policy["include"]))
        self.assertTrue(any("原始数据" in t for t in policy["skip"]))

    def test_skill_keeps_pkparam_even_without_space(self):
        focused = focus_content_for_model(SYNTH, PK_SKILL)
        self.assertIn("### Sheet: PK参数", focused)
        self.assertIn("Cl_obs", focused)
        self.assertIn("### Sheet: 封面", focused)
        self.assertNotIn("### Sheet: 原始数据", focused)
        self.assertNotIn("### Sheet: 试验设计", focused)

    def test_skill_include_only_cover_and_params_drops_summary(self):
        skill = """
## 读取范围
- 读取：`封面`、`PK 参数`
- 跳过：`原始数据`、`试验设计`
"""
        focused = focus_content_for_model(SYNTH, skill)
        self.assertIn("PK参数", focused)
        self.assertIn("封面", focused)
        self.assertNotIn("结果汇总", focused)
        self.assertNotIn("原始数据", focused)

    def test_no_skill_self_selects_conclusion_sheets(self):
        focused = focus_content_for_model(SYNTH, None)
        self.assertIn("PK参数", focused)
        self.assertIn("结果汇总", focused)
        self.assertNotIn("原始数据", focused)
        self.assertNotIn("试验设计", focused)

    def test_mms_skill_skips_raw(self):
        skill = """
## 读取范围
- 读取：`Signature`、`Summary`
- 跳过：`Raw Data`、`Materials`
"""
        text = "\n".join([
            "### Sheet: Signature",
            "report",
            "### Sheet: Summary",
            "T1/2 12",
            "### Sheet: Raw Data",
            "peak",
            "### Sheet: Materials",
            "lot",
        ])
        focused = focus_content_for_model(text, skill)
        self.assertIn("Summary", focused)
        self.assertIn("Signature", focused)
        self.assertNotIn("Raw Data", focused)
        self.assertNotIn("Materials", focused)


if __name__ == "__main__":
    unittest.main()
