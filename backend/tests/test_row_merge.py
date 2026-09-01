import unittest

from app.services.row_merge import merge_extracted_rows, summarize_chunk_notes


class MergeExtractedRowsTest(unittest.TestCase):
    def test_same_id_fills_empty_and_dedupes(self):
        rows = [
            {"cpds_id": "HW1", "ic50_nm": "51", "inhib_top": ""},
            {"cpds_id": "HW1", "ic50_nm": "51", "inhib_top": ""},
            {"cpds_id": "HW2", "ic50_nm": "180"},
        ]
        merged, conflicts = merge_extracted_rows(rows, key_field="cpds_id")
        ids = [r["cpds_id"] for r in merged]
        self.assertEqual(ids, ["HW1", "HW2"])
        self.assertEqual(merged[0]["ic50_nm"], "51")
        self.assertEqual(conflicts, [])

    def test_conflicting_values_keep_first_and_flag(self):
        rows = [
            {"cpds_id": "HW1", "iv_1mpk_vss_l_kg": "1.21", "po_5_mpk_tmax_hr": "1.33"},
            {"cpds_id": "HW1", "iv_1mpk_vss_l_kg": "0.94", "po_5_mpk_tmax_hr": "1"},
        ]
        merged, conflicts = merge_extracted_rows(rows, key_field="cpds_id")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["iv_1mpk_vss_l_kg"], "1.21")
        self.assertIn("iv_1mpk_vss_l_kg", merged[0].get("_conflicts") or {})
        fields = {c["field"] for c in conflicts}
        self.assertIn("iv_1mpk_vss_l_kg", fields)
        self.assertIn("po_5_mpk_tmax_hr", fields)

    def test_rows_without_id_are_kept_separate(self):
        rows = [
            {"cpds_id": "", "ic50_nm": "1"},
            {"cpds_id": "", "ic50_nm": "2"},
        ]
        merged, _ = merge_extracted_rows(rows, key_field="cpds_id")
        self.assertEqual(len(merged), 2)

    def test_close_floats_are_not_conflicts(self):
        rows = [
            {"cpds_id": "HW1", "cl": "0.427"},
            {"cpds_id": "HW1", "cl": "0.42715938"},
        ]
        merged, conflicts = merge_extracted_rows(rows, key_field="cpds_id")
        self.assertEqual(conflicts, [])
        self.assertFalse(merged[0].get("_conflicts"))


class SummarizeChunkNotesTest(unittest.TestCase):
    def test_hides_empty_chunk_warnings(self):
        chunks = [
            ("封面没有 Assay Summary，输出空数组", []),
            ("Protocol 页无结论", []),
            ("已定位 HW350003A，IC50 为 >30", [{"cpds_id": "HW350003A"}]),
        ]
        text = summarize_chunk_notes(chunks)
        self.assertIn("3 段", text)
        self.assertIn("1 段抽出", text)
        self.assertIn("HW350003A", text)
        self.assertNotIn("没有 Assay Summary", text)
        self.assertNotIn("Protocol 页无结论", text)
