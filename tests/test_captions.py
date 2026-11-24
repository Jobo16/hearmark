"""Caption source selection must preserve the original speech language."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

script = Path(__file__).resolve().parents[1] / ".agents/skills/hearmark/scripts/hearmark.py"
spec = importlib.util.spec_from_file_location("hearmark", script)
hearmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hearmark)


class CaptionsTest(unittest.TestCase):
    def test_accepts_https_links_for_yt_dlp_extractors(self):
        for url in (
            "https://www.youtube.com/watch?v=test",
            "https://www.bilibili.com/video/BV1jg4y1A7AU/",
            "https://b23.tv/example",
            "https://media.example/video/123",
        ):
            with self.subTest(url=url):
                self.assertTrue(hearmark.validate_url(url))

    def test_rejects_non_https_and_credentialed_urls(self):
        self.assertFalse(hearmark.validate_url("http://www.bilibili.com/video/BV1test"))
        self.assertFalse(hearmark.validate_url("https://user:secret@bilibili.com/video/BV1test"))
        self.assertFalse(hearmark.validate_url("https:///video"))

    def test_human_original_precedes_auto_and_translation(self):
        info = {"language": "en", "subtitles": {"en": [{}], "fr": [{}]}, "automatic_captions": {"en-orig": [{}]}}
        calls = []
        with tempfile.TemporaryDirectory() as temp:
            def run(arguments, _browser):
                calls.append(arguments)
                if "--dump-single-json" in arguments:
                    return 0, [json.dumps(info)], None, ["public"]
                (Path(temp) / "caption.en.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello\n")
                return 0, [], None, ["public"]
            with patch.object(hearmark, "run_with_browser_fallback", side_effect=run):
                segments, _, _, origin, language = hearmark.try_captions("https://youtube.com/watch?v=test", Path(temp), "auto", "none")
        self.assertEqual((origin, language, segments[0]["text"]), ("manual_captions", "en", "Hello"))
        self.assertIn("--write-subs", calls[1])
        self.assertNotIn("--write-auto-subs", calls[1])

    def test_auto_original_when_human_missing(self):
        self.assertEqual(hearmark.caption_track({"en-de": [{}], "en-orig": [{}]}, "en", "auto"), "en-orig")
        self.assertIsNone(hearmark.caption_track({"en-de": [{}]}, "en", "auto"))

    def test_rechecks_empty_caption_list_with_local_browser_session(self):
        public_info = {"language": "zh-CN", "subtitles": {}, "automatic_captions": {}}
        signed_in_info = {"language": "zh-CN", "subtitles": {"zh-CN": [{}]}, "automatic_captions": {}}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)

            def browser_fallback(arguments, _browser):
                if "--dump-single-json" in arguments:
                    return 0, [json.dumps(public_info)], None, ["public"]
                (directory / "caption.zh-CN.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n你好\n")
                return 0, [], "chrome", ["public", "chrome"]

            with patch.object(hearmark, "run_with_browser_fallback", side_effect=browser_fallback), \
                 patch.object(hearmark, "browser_candidates", return_value=["chrome"]), \
                 patch.object(hearmark, "run_ytdlp", return_value=(0, [json.dumps(signed_in_info)])):
                segments, browser, tried, origin, language = hearmark.try_captions(
                    "https://www.bilibili.com/video/BV1test", directory, "auto", "auto"
                )
        self.assertEqual((segments[0]["text"], browser, origin, language), ("你好", "chrome", "manual_captions", "zh-CN"))
        self.assertEqual(tried, ["public", "chrome"])


if __name__ == "__main__":
    unittest.main()
