import unittest

from app.i18n import translate_api_detail, wants_english


class ApiErrorLocalizationTests(unittest.TestCase):
    def test_accept_language_detection(self):
        self.assertTrue(wants_english("en-US,en;q=0.9"))
        self.assertTrue(wants_english("en"))
        self.assertFalse(wants_english("zh-CN"))
        self.assertFalse(wants_english(None))

    def test_exact_message_is_translated(self):
        self.assertEqual(
            translate_api_detail("推理节点不存在", "en-US,en;q=0.9"),
            "Inference node not found",
        )
        self.assertEqual(
            translate_api_detail("RunningHub 端点工作流已关闭", "en"),
            "RunningHub endpoint workflows are disabled",
        )

    def test_dynamic_messages_are_translated(self):
        self.assertEqual(
            translate_api_detail("单个文件不能超过 20 MB", "en"),
            "Each file must be at most 20 MB",
        )
        self.assertEqual(
            translate_api_detail("不支持的素材类型：bad.txt", "en"),
            "Unsupported file type: bad.txt",
        )
        self.assertEqual(
            translate_api_detail("Music3 时长范围为 1–300 秒", "en"),
            "Music3 duration must be between 1 and 300 seconds",
        )

    def test_chinese_and_unknown_messages_are_unchanged(self):
        self.assertEqual(translate_api_detail("任务不存在", "zh-CN"), "任务不存在")
        self.assertEqual(translate_api_detail("upstream exploded", "en"), "upstream exploded")


if __name__ == "__main__":
    unittest.main()
