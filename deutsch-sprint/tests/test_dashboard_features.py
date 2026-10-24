import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DashboardFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.source = (ROOT / "dashboard.template.html").read_text(encoding="utf-8")

    def test_dashboard_embeds_exact_prompt_markdown_sources(self):
        match = re.search(r'<script type="application/json" id="prompt-data">(.*?)</script>', self.html, re.S)
        self.assertIsNotNone(match)
        prompts = json.loads(match.group(1))
        self.assertEqual(prompts["speaking"], (ROOT / "p3-p4-prompts/speaking-coach.md").read_text(encoding="utf-8"))
        self.assertEqual(prompts["writing"], (ROOT / "p3-p4-prompts/writing-coach.md").read_text(encoding="utf-8"))

    def test_error_import_supports_markdown_and_tsv_headers_and_deduplicates(self):
        self.assertIn("function parseErrorTable(source)", self.source)
        self.assertIn("表头未识别", self.source)
        self.assertIn("重复记录将跳过", self.source)
        self.assertIn("data-action=\"preview-error-import\"", self.source)
        self.assertIn("data-action=\"import-errors\"", self.source)
        self.assertIn("toLocaleLowerCase()", self.source)


if __name__ == "__main__":
    unittest.main()
