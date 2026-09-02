import unittest

from app.schemas import ColumnDef
from app.services.ai_service import (
    compact_file_for_qa,
    extra_body_for_model,
    friendly_llm_error,
    report_stream_progress,
    split_file_chunks,
    strip_model_noise,
    _split_chat_reply,
)


class SplitFileChunksTest(unittest.TestCase):
    def test_small_content_stays_one_chunk(self):
        text = "hello " * 10
        self.assertEqual(split_file_chunks(text, max_chars=1000), [text])

    def test_splits_on_sheet_headers(self):
        a = "### Sheet: A\n" + ("A" * 40)
        b = "### Sheet: B\n" + ("B" * 40)
        chunks = split_file_chunks(a + "\n" + b, max_chars=60)
        self.assertGreaterEqual(len(chunks), 2)
        self.assertTrue(any("Sheet: A" in c for c in chunks))
        self.assertTrue(any("Sheet: B" in c for c in chunks))
        self.assertTrue(all("已截断" not in c for c in chunks))


class CompactFileForQaTest(unittest.TestCase):
    def test_short_file_kept(self):
        text = "abc"
        out = compact_file_for_qa(text, {"chars": 3, "truncated": False}, limit=100)
        self.assertIn("abc", out)
        self.assertNotIn("已截断", out)

    def test_long_file_uses_head_and_tail(self):
        text = "H" * 80 + "T" * 80
        out = compact_file_for_qa(text, {"chars": 160, "truncated": False}, limit=40)
        self.assertIn("开头", out)
        self.assertIn("结尾", out)
        self.assertIn("H", out)
        self.assertIn("T", out)
        self.assertNotIn("已截断", out)


class FriendlyLlmErrorTest(unittest.TestCase):
    def test_504(self):
        msg = friendly_llm_error(RuntimeError("Error code: 504"))
        self.assertIn("超时", msg)
        self.assertIn("504", msg)

    def test_429_quota(self):
        msg = friendly_llm_error(RuntimeError("Error code: 429 - 已达到 Token Plan 用量上限"))
        self.assertIn("配额", msg)
        self.assertIn("429", msg)

    def test_unsupported_qwen_on_wrong_gateway(self):
        msg = friendly_llm_error(RuntimeError(
            "Error code: 400 - {'success': False, 'message': '不支持的模型或无可用服务商: qwen3.6-flash', 'data': None}"
        ))
        self.assertIn("不提供这个模型", msg)
        self.assertIn("百炼", msg)
        self.assertNotIn("Error code: 400", msg)

    def test_extra_body_only_for_minimax(self):
        self.assertEqual(extra_body_for_model("MiniMax-M2.7-highspeed"), {"reasoning_split": True})
        self.assertEqual(extra_body_for_model("qwen3.6-flash"), {})


class MiniMaxThinkParseTest(unittest.TestCase):
    def test_strip_think_block(self):
        raw = "<think>内部复述 <<<ROWS>>> []</think>\n1. 步骤\n<<<ROWS>>>\n[{\"cpds_id\":\"HW1\"}]"
        self.assertNotIn("<think>", strip_model_noise(raw))
        self.assertIn("<<<ROWS>>>", strip_model_noise(raw))

    def test_split_uses_visible_rows_not_think_example(self):
        cols = [ColumnDef(field="cpds_id", title="ID"), ColumnDef(field="ic50_um", title="IC50")]
        raw = (
            "<think>输出协议是 <<<ROWS>>> [{\"cpds_id\":\"示例\"}]</think>\n"
            "1. 已定位 Assay Summary\n"
            "<<<ROWS>>>\n"
            "[{\"cpds_id\": \"HW350003A\", \"ic50_um\": \"\"}]\n"
            "<<<ROWS>>>\n"
        )
        note, rows = _split_chat_reply(raw, cols)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cpds_id"], "HW350003A")
        self.assertNotIn("<think>", note)


class StreamProgressTest(unittest.TestCase):
    def test_mapping_line_becomes_generating(self):
        seen = set()
        got = []
        report_stream_progress("1. 已加载 Skill\n2. 解析 2 个附件\n3. 映射 10 列", seen, got.append)
        self.assertEqual(got, ["正在抽取并生成结果…"])
        report_stream_progress("3. 映射 10 列\n<<<ROWS>>>\n[{", seen, got.append)
        self.assertEqual(got[-1], "正在生成结果…")
        report_stream_progress("<<<ROWS>>>\n[{}]", seen, got.append)
        self.assertEqual(got.count("正在生成结果…"), 1)


if __name__ == "__main__":
    unittest.main()
