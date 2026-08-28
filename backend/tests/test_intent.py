import unittest

from app.services.intent import classify_intent


class ClassifyIntentTest(unittest.TestCase):
    def test_empty_with_files_is_recognize(self):
        self.assertEqual(classify_intent("", has_files=True), "recognize")
        self.assertEqual(classify_intent("   ", has_files=True), "recognize")

    def test_empty_without_files_is_chat(self):
        self.assertEqual(classify_intent("", has_files=False), "chat")

    def test_recognize_keywords(self):
        for text in ("请识别", "重新识别这批", "帮我导入", "提取数据", "填表", "覆盖表格", "再导一次"):
            self.assertEqual(classify_intent(text, True), "recognize", text)

    def test_why_is_chat_even_with_files(self):
        self.assertEqual(classify_intent("为啥截断", True), "chat")
        self.assertEqual(classify_intent("为什么会留空", True), "chat")
        self.assertEqual(classify_intent("解释一下均值怎么取", True), "chat")
        self.assertEqual(classify_intent("是不是截断了", True), "chat")
        self.assertEqual(classify_intent("对吗", True), "chat")

    def test_dont_recognize_wins_over_keyword(self):
        self.assertEqual(classify_intent("先别识别", True), "chat")

    def test_question_particles_are_chat(self):
        self.assertEqual(classify_intent("这是均值吗？", True), "chat")
        self.assertEqual(classify_intent("还能再补一列呢", True), "chat")

    def test_rule_without_rerecognize_is_chat(self):
        self.assertEqual(classify_intent("对照请过滤掉", True), "chat")


if __name__ == "__main__":
    unittest.main()
