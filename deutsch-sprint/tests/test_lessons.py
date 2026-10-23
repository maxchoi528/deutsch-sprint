import contextlib
import io
import json
import math
from pathlib import Path
import re
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "p1-reader"))
from validate_lessons import reader_sentences, validate_collection  # noqa: E402


class LessonEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collection = json.loads(
            (PROJECT_ROOT / "p1-reader" / "lessons.json").read_text(encoding="utf-8")
        )
        cls.lesson = next(
            lesson for lesson in cls.collection["lessons"] if lesson["id"] == "digitale-verwaltung"
        )
        cls.sentences = reader_sentences(cls.lesson["text"])

    def test_third_lesson_true_false_uses_final_evidence_sentence(self):
        question = self.lesson["questions"][0]
        evidence = self.sentences[question["evidence_sentence_index"]]
        self.assertEqual(question["evidence_sentence_index"], 20)
        self.assertTrue(evidence.startswith("Werden diese Hinweise ernst genommen"))

    def test_third_lesson_third_question_uses_process_tracking_sentence(self):
        question = self.lesson["questions"][2]
        evidence = self.sentences[question["evidence_sentence_index"]]
        self.assertEqual(question["evidence_sentence_index"], 14)
        self.assertTrue(evidence.startswith("Wenn eine Eingabe an mehreren Stellen bearbeitet wird"))

    def test_every_existing_question_and_gloss_passes_validator(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            errors = validate_collection(self.collection)
        self.assertEqual(errors, [])
        self.assertIn("[digitale-verwaltung Q1 · sentence 20]", output.getvalue())
        self.assertIn("[digitale-verwaltung Q3 · sentence 14]", output.getvalue())

    def test_new_b2_lessons_meet_content_and_review_requirements(self):
        lessons = [lesson for lesson in self.collection["lessons"] if lesson["id"].startswith("b2-")]
        self.assertGreaterEqual(len(lessons), 6)
        for lesson in lessons:
            with self.subTest(lesson=lesson["id"]):
                plain_text = re.sub(r"\{([^{}|]+)\|[^{}|]+\}", r"\1", lesson["text"])
                word_count = len(re.findall(r"\S+", plain_text))
                self.assertIn(lesson["level"], {"B2", "B2+"})
                self.assertGreaterEqual(word_count, 180)
                self.assertLessEqual(word_count, 260)
                self.assertGreaterEqual(len(lesson["glosses"]), 12)
                self.assertGreaterEqual(len(lesson["glosses"]), math.ceil(word_count * 0.05))
                self.assertEqual(lesson["review_status"], "ai-generated-unreviewed")
                self.assertEqual(len(lesson["questions"]), 3)
                self.assertGreaterEqual(len(lesson["grammar_focus"]), 2)
                self.assertNotEqual(lesson["summary_zh"], "AI 生成的练习摘要，尚未导师审校。")
                self.assertEqual({q["type"] for q in lesson["questions"]}, {"对错", "选择", "配对"})
                for gloss in lesson["glosses"]:
                    self.assertRegex(gloss["zh"], r"[\u3400-\u9fff]", "Chinese meanings must not be German placeholders")


if __name__ == "__main__":
    unittest.main()
