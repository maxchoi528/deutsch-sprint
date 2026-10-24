import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SyllabusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "syllabus.json").read_text(encoding="utf-8"))
        cls.schema = json.loads((ROOT / "syllabus.schema.json").read_text(encoding="utf-8"))
        cls.dashboard_template = (ROOT / "dashboard.template.html").read_text(encoding="utf-8")
        cls.dashboard = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.reader_template = (ROOT / "p1-reader" / "reader.template.html").read_text(encoding="utf-8")
        cls.lessons = json.loads((ROOT / "p1-reader" / "lessons.json").read_text(encoding="utf-8"))["lessons"]

    def test_schema_and_all_sixteen_week_records(self):
        self.assertEqual(self.schema["properties"]["schemaVersion"]["const"], 1)
        self.assertEqual(self.data["schemaVersion"], 1)
        self.assertEqual([week["week"] for week in self.data["weeks"]], list(range(1, 17)))
        self.assertEqual([week["stage"] for week in self.data["weeks"]], ["A"]*4+["B"]*5+["C"]*4+["D"]*3)
        required = set(self.schema["$defs"]["week"]["required"])
        lesson_ids = {lesson["id"] for lesson in self.lessons}
        for week in self.data["weeks"]:
            with self.subTest(week=week["week"]):
                self.assertTrue(required.issubset(week))
                self.assertIn(week["reading_lesson_id"], lesson_ids)
                self.assertEqual(set(week["daily_tasks"]), {"anki", "deep", "speaking", "listening", "writing"})
                self.assertTrue(all(isinstance(text, str) and text for text in week["daily_tasks"].values()))

    def test_dashboard_embeds_the_same_syllabus_and_preserves_legacy_daily_records(self):
        self.assertIn("old.dailyTasks && typeof old.dailyTasks === 'object' ? old.dailyTasks : {}", self.dashboard_template)
        self.assertIn("data-syllabus-task", self.dashboard_template)
        self.assertIn("今日任务 · 五个学习块", self.dashboard_template)
        encoded = re.search(r'<script type="application/json" id="syllabus-data">(.*?)</script>', self.dashboard, re.S)
        self.assertIsNotNone(encoded)
        self.assertEqual(json.loads(encoded.group(1)), self.data)
        self.assertEqual(self.dashboard_template.count("__SYLLABUS_JSON__"), 1)
        self.assertIn("new URLSearchParams(location.search).get('lesson')", self.reader_template)

    def test_validator_passes(self):
        import sys
        sys.path.insert(0, str(ROOT))
        import validate_syllabus
        self.assertEqual(validate_syllabus.validate(), [])


if __name__ == "__main__":
    unittest.main()
