import unittest

from app.schemas import ColumnDef
from app.services.row_merge import (
    compose_extraction_reply,
    infer_merge_key_fields,
    merge_extracted_rows,
    summarize_chunk_notes,
)


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

    def test_rounded_means_are_not_conflicts(self):
        rows = [
            {"cpds_id": "HW1", "t12": "2.02", "tmax": "1.33"},
            {"cpds_id": "HW1", "t12": "2.02490873", "tmax": "1.33333333"},
        ]
        merged, conflicts = merge_extracted_rows(rows, key_field="cpds_id")
        self.assertEqual(conflicts, [])
        self.assertFalse(merged[0].get("_conflicts"))

    def test_percent_f_gap_is_still_a_conflict(self):
        rows = [
            {"cpds_id": "HW1", "po_5_mpk_pct_f": "98.9"},
            {"cpds_id": "HW1", "po_5_mpk_pct_f": "97.4497814045999"},
        ]
        merged, conflicts = merge_extracted_rows(rows, key_field="cpds_id")
        self.assertEqual(merged[0]["po_5_mpk_pct_f"], "98.9")
        self.assertTrue(conflicts)

    def test_preserves_existing_conflicts_when_merged_again(self):
        rows = [{
            "cpds_id": "HW1",
            "iv_1mpk_vss_l_kg": "1.21",
            "_conflicts": {"iv_1mpk_vss_l_kg": ["1.21", "0.94"]},
        }]
        merged, conflicts = merge_extracted_rows(rows, key_field="cpds_id")
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["_conflicts"]["iv_1mpk_vss_l_kg"], ["1.21", "0.94"])
        self.assertEqual(conflicts, [])

    def test_merges_inherited_conflicts_across_files(self):
        rows = [
            {
                "cpds_id": "HW1",
                "cl": "0.4",
                "_conflicts": {"cl": ["0.4", "0.5"]},
            },
            {"cpds_id": "HW1", "vss": "1.2"},
        ]
        merged, _ = merge_extracted_rows(rows, key_field="cpds_id")
        self.assertEqual(merged[0]["cl"], "0.4")
        self.assertEqual(merged[0]["vss"], "1.2")
        self.assertEqual(merged[0]["_conflicts"]["cl"], ["0.4", "0.5"])

    def test_same_cpds_different_treatment_group_stays_separate(self):
        """Langendorff：同一化合物多处理组应保留多行，不能按 cpds_id 压成 1 行。"""
        groups = ["control 1", "control 2", "0.4 μM", "2 μM", "10 μM", "washout", "Dofetilide"]
        rows = [
            {
                "cpds_id": "HW181125",
                "study_id": "ST-001",
                "treatment_group": g,
                "qt_interval_ms": str(100 + i),
            }
            for i, g in enumerate(groups)
        ]
        cols = [
            ColumnDef(field="cpds_id", title="Cpds ID"),
            ColumnDef(field="study_id", title="Study ID"),
            ColumnDef(field="treatment_group", title="Treatment Group"),
            ColumnDef(field="qt_interval_ms", title="QT"),
        ]
        key_fields = infer_merge_key_fields(cols)
        self.assertEqual(key_fields, ["cpds_id", "study_id", "treatment_group"])
        merged, conflicts = merge_extracted_rows(rows, key_fields=key_fields)
        self.assertEqual(len(merged), 7)
        self.assertEqual([r["treatment_group"] for r in merged], groups)
        self.assertEqual(conflicts, [])

    def test_duplicate_same_composite_key_still_merges(self):
        rows = [
            {"cpds_id": "HW1", "treatment_group": "control", "hr": "80"},
            {"cpds_id": "HW1", "treatment_group": "control", "hr": "80", "pr": "120"},
        ]
        key_fields = ["cpds_id", "treatment_group"]
        merged, conflicts = merge_extracted_rows(rows, key_fields=key_fields)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["hr"], "80")
        self.assertEqual(merged[0]["pr"], "120")

    def test_infer_merge_key_fields_pk_table(self):
        cols = [ColumnDef(field="cpds_id", title="ID"), ColumnDef(field="cl", title="CL")]
        self.assertEqual(infer_merge_key_fields(cols), ["cpds_id"])


class InferMergeKeyFieldsTest(unittest.TestCase):
    def test_includes_treatment_group_when_present(self):
        cols = [
            ColumnDef(field="cpds_id", title="ID"),
            ColumnDef(field="treatment_group", title="Group"),
        ]
        self.assertEqual(infer_merge_key_fields(cols), ["cpds_id", "treatment_group"])


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


class ComposeExtractionReplyTest(unittest.TestCase):
    def test_multi_file_hides_empty_attachment_notes(self):
        notes = [
            ("附件 1/3：封面找不到主源", []),
            ("附件 2/3：抽出 HW1", [{"cpds_id": "HW1"}]),
            ("附件 3/3：方法页无结果", []),
        ]
        merged = [{"cpds_id": "HW1"}]
        text = compose_extraction_reply(
            notes, merged, raw_n=2, n_items=3, new_conflicts=[],
        )
        self.assertIn("抽出 HW1", text)
        self.assertNotIn("找不到主源", text)
        self.assertNotIn("方法页无结果", text)
        self.assertIn("2 行 → 1 行", text)
        self.assertIn("化合物 ID", text)

    def test_single_file_keeps_inner_pagination_summary(self):
        inner = "共 3 段：1 段抽出数据，2 段无抽出结果（已忽略，避免和表内数据矛盾）。"
        text = compose_extraction_reply(
            [(inner, [{"cpds_id": "HW1"}])],
            [{"cpds_id": "HW1"}],
            raw_n=1,
            n_items=1,
            new_conflicts=[],
        )
        self.assertEqual(text, inner)

