import unittest

from app.schemas import ColumnDef
from app.services.table_edit import apply_local_edit, looks_like_local_edit, parse_decimal_places
from app.services.ai_service import table_rows_context


COLS = [
    ColumnDef(field="cpds_id", title="ID", type="text"),
    ColumnDef(field="cl", title="CL", type="number"),
    ColumnDef(field="auc", title="AUC", type="number"),
]


class TableEditTest(unittest.TestCase):
    def test_parse_two_places(self):
        self.assertEqual(parse_decimal_places("小数位数超过2位的都要改成2位小数"), 2)
        self.assertEqual(parse_decimal_places("全部保留两位小数"), 2)
        self.assertEqual(parse_decimal_places("改成3位小数"), 3)

    def test_looks_like_edit(self):
        self.assertTrue(looks_like_local_edit("小数位数超过2位的都要改成2位小数"))
        self.assertFalse(looks_like_local_edit("为啥HW1没有"))

    def test_rounds_only_excess_decimals(self):
        rows = [
            {"cpds_id": "HW1", "cl": "0.2046234", "auc": "12.3"},
            {"cpds_id": "HW2", "cl": "1.2", "auc": "100"},
        ]
        reply, out, ok = apply_local_edit("小数位数超过2位的都要改成2位小数", rows, COLS)
        self.assertTrue(ok)
        self.assertIn("没有重新识别", reply)
        self.assertEqual(out[0]["cl"], "0.20")
        self.assertEqual(out[0]["auc"], "12.3")
        self.assertEqual(out[0]["cpds_id"], "HW1")
        self.assertEqual(out[1]["cl"], "1.2")
        self.assertEqual(out[1]["auc"], "100")

    def test_empty_table_not_ok(self):
        reply, out, ok = apply_local_edit("改成2位小数", [], COLS)
        self.assertFalse(ok)
        self.assertEqual(out, [])
        self.assertIn("还没有", reply)

    def test_table_rows_context_lists_ids(self):
        text = table_rows_context([{"cpds_id": "HW1", "cl": "0.20"}], COLS)
        self.assertIn("HW1", text)
        self.assertIn("0.20", text)
        self.assertIn("已导入 1 行", text)


if __name__ == "__main__":
    unittest.main()
