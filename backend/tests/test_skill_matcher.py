import unittest

from app.schemas import ColumnDef
from app.services.skill_matcher import pick_by_rules, resolve_skill


MMS = {
    "id": 1,
    "name": "MMS · 人福 D-RF 版式",
    "content": """
## 匹配线索
- 文件名含 `-MMS-`，或标题含 Metabolic Stability + Liver Microsomes
- Sheet 含 Signature, Summary
## 目标结果表
`MMS`
## 字段映射
cpds_id remain30_human t12_human
""",
}
HCT = {
    "id": 2,
    "name": "HCT116 增殖",
    "content": """
## 匹配线索
- HCT116 细胞增殖抑制检测报告
## 目标结果表
`SW48/HCT116增殖试验`
ic50_nm
""",
}


class SkillMatcherTest(unittest.TestCase):
    def test_specified_skill_id_wins(self):
        picked = resolve_skill(
            skills=[MMS, HCT],
            skill_id=2,
            auto_skill=True,
            table_name="MMS",
            columns=[],
            file_content="Liver Microsomes MMS",
            use_llm=False,
        )
        self.assertEqual(picked["skill_id"], 2)
        self.assertFalse(picked["skill_auto"])
        self.assertEqual(picked["skill_name"], HCT["name"])

    def test_auto_picks_mms(self):
        cols = [ColumnDef(field="remain30_human", title="Human 30min"), ColumnDef(field="t12_human", title="T1/2")]
        picked = pick_by_rules(
            [MMS, HCT],
            table_name="MMS",
            columns=cols,
            file_content="Report: Metabolic Stability in Human Liver Microsomes. Sheets: Signature, Summary.",
        )
        self.assertIsNotNone(picked)
        self.assertEqual(picked["id"], 1)

    def test_no_match_returns_none(self):
        picked = pick_by_rules(
            [MMS, HCT],
            table_name="Binding Assay",
            columns=[ColumnDef(field="cell_line", title="Cell Line")],
            file_content="random invoice text without assay clues",
        )
        self.assertIsNone(picked)

    def test_auto_false_uses_baseline_only(self):
        picked = resolve_skill(
            skills=[MMS],
            skill_id=None,
            auto_skill=False,
            table_name="MMS",
            columns=[],
            file_content="MMS Liver Microsomes",
            use_llm=False,
        )
        self.assertIsNone(picked["skill_id"])
        self.assertFalse(picked["skill_auto"])
        self.assertIn("基线", picked["skill_reason"])


if __name__ == "__main__":
    unittest.main()
