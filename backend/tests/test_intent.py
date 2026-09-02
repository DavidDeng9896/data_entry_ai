import unittest

from app.services.intent import classify_intent


class ClassifyIntentTest(unittest.TestCase):
    def test_empty_with_files_is_recognize(self):
        self.assertEqual(classify_intent("", has_files=True), "recognize")
        self.assertEqual(classify_intent("   ", has_files=True), "recognize")

    def test_empty_without_files_is_chat(self):
        self.assertEqual(classify_intent("", has_files=False), "chat")

    def test_recognize_keywords(self):
        for text in ("请识别", "重新识别这批", "帮我导入", "提取数据", "填表", "覆盖表格", "再导一次", "对照请过滤掉"):
            self.assertEqual(classify_intent(text, True, has_rows=True), "recognize", text)

    def test_why_is_chat_even_with_files(self):
        self.assertEqual(classify_intent("为啥截断", True, True), "chat")
        self.assertEqual(classify_intent("为什么会留空", True, True), "chat")
        self.assertEqual(classify_intent("解释一下均值怎么取", True, True), "chat")
        self.assertEqual(classify_intent("是不是截断了", True, True), "chat")
        self.assertEqual(classify_intent("对吗", True, True), "chat")
        self.assertEqual(classify_intent("为啥HW350003A化合物数据没有？", True, True), "chat")

    def test_dont_recognize_wins_over_keyword(self):
        self.assertEqual(classify_intent("先别识别", True, True), "chat")

    def test_question_particles_are_chat(self):
        self.assertEqual(classify_intent("这是均值吗？", True, True), "chat")
        self.assertEqual(classify_intent("还能再补一列呢", True, True), "chat")

    def test_decimal_edit_not_reimport(self):
        text = "小数位数超过2位的都要改成2位小数"
        self.assertEqual(classify_intent(text, True, has_rows=True), "edit")
        self.assertEqual(classify_intent(text, True, has_rows=False), "chat")

    def test_followup_without_keyword_is_chat_when_table_filled(self):
        self.assertEqual(classify_intent("这个 CL 看起来偏高", True, has_rows=True), "chat")


if __name__ == "__main__":
    unittest.main()
