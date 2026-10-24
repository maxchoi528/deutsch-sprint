import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "p1-reader" / "tools"
sys.path.insert(0, str(ROOT / "p1-reader"))
sys.path.insert(0, str(TOOLS))
from validate_lessons import validate_file  # noqa: E402
from skeleton_from_text import make_skeleton  # noqa: E402
from merge_lessons import merge_into  # noqa: E402
from mark_reviewed import mark_reviewed  # noqa: E402


class AuthoringToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = json.loads((ROOT / "p1-reader" / "lessons.json").read_text(encoding="utf-8"))["lessons"]
        cls.new_lessons = cls.lessons[-6:]

    def test_six_new_lessons_match_word_gloss_and_source_requirements(self):
        self.assertEqual(len(self.new_lessons), 6)
        for lesson in self.new_lessons:
            plain = lesson["text"]
            import re
            plain = re.sub(r"\{([^{}|]+)\|([^{}|]+)\}", r"\1", plain)
            count = len(plain.split())
            with self.subTest(lesson=lesson["id"]):
                self.assertGreaterEqual(count, 220)
                self.assertLessEqual(count, 320)
                self.assertEqual(lesson["source"], "original-ai")
                self.assertEqual(lesson["review_status"], "ai-generated-unreviewed")
                self.assertTrue(lesson["grammar_target"])
                self.assertEqual(len(lesson["questions"]), 3)
                self.assertGreaterEqual(len(lesson["glosses"]), 12)
                self.assertTrue(all(q["answer"] in q["options"] for q in lesson["questions"]))

    def test_single_lesson_json_is_supported_by_file_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "one-lesson.json"
            path.write_text(json.dumps(self.new_lessons[0], ensure_ascii=False), encoding="utf-8")
            self.assertEqual(validate_file(path), [])
            result = subprocess.run([sys.executable, str(ROOT / "p1-reader/validate_lessons.py"), "--file", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_skeleton_counts_words_and_indexes_reader_sentences(self):
        skeleton = make_skeleton("Ein erster Satz.\n\nEin zweiter Satz!", "draft", "Entwurf", "B2", "Informationstext")
        self.assertEqual(skeleton["word_count"], 6)
        self.assertEqual([row["index"] for row in skeleton["sentences"]], [0, 1])
        self.assertEqual(skeleton["source"], "user-provided")

    def test_merge_rejects_user_text_and_accepts_valid_original(self):
        base = {"schemaVersion": 1, "lessons": []}
        lesson = self.new_lessons[0]
        errors = merge_into(base, [lesson])
        self.assertEqual(errors, [])
        self.assertEqual(len(base["lessons"]), 1)
        private_text = {**lesson, "id": "private", "source": "user-provided"}
        errors = merge_into({"schemaVersion": 1, "lessons": []}, [private_text])
        self.assertTrue(any("p1-reader/local/" in error for error in errors))

    def test_mark_reviewed_records_tutor_and_date(self):
        collection = {"lessons": [{"id": "draft", "review_status": "ai-generated-unreviewed"}]}
        self.assertTrue(mark_reviewed(collection, "draft", "Tutor", "2026-10-24"))
        self.assertEqual(collection["lessons"][0]["review_status"], "tutor-reviewed")
        self.assertEqual(collection["lessons"][0]["reviewed_by"], "Tutor")
        self.assertEqual(collection["lessons"][0]["reviewed_at"], "2026-10-24")
        with self.assertRaises(ValueError):
            mark_reviewed(collection, "draft", "Tutor", "yesterday")


if __name__ == "__main__":
    unittest.main()
