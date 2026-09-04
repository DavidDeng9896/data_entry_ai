import unittest

from app.services.skill_merge import merge_skill_markdown, mock_merge_skill_markdown


class SkillMergeTest(unittest.TestCase):
    def test_mock_merge_keeps_sections_from_both(self):
        base = """# PK · 旧版式

## 匹配线索
- 旧供应商

## 目标结果表
Dog PK

## 字段映射
| 目标字段 | 源 |
| --- | --- |
| `cpds_id` | 旧 ID |

## 不映射
旧方法页
"""
        draft = """# PK · 新版式

## 匹配线索
- 新供应商

## 目标结果表
Dog PK

## 字段映射
| 目标字段 | 源 |
| --- | --- |
| `iv_1mpk_cl_l_h_kg` | Cl_obs |

## 不映射
原始数据
"""
        out = mock_merge_skill_markdown(base, draft, name="PK · 合并")
        self.assertIn("匹配线索", out)
        self.assertIn("旧供应商", out)
        self.assertIn("新供应商", out)
        self.assertIn("iv_1mpk_cl_l_h_kg", out)
        self.assertIn("cpds_id", out)

    def test_merge_skill_markdown_mock_path(self):
        text = merge_skill_markdown("# A\n\n## 匹配线索\n- x\n", "# B\n\n## 字段映射\n- y\n", force_mock=True)
        self.assertTrue(text.strip())
        self.assertIn("匹配线索", text)
