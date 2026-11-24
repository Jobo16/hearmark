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


if __name__ == "__main__":
    unittest.main()
