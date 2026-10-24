import contextlib
import io
import json
import math
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch


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
                self.assertTrue({q["type"] for q in lesson["questions"]} <= {"对错", "选择", "选择（细节）", "推断", "立场"})
                for gloss in lesson["glosses"]:
                    self.assertRegex(gloss["zh"], r"[\u3400-\u9fff]", "Chinese meanings must not be German placeholders")
                    self.assertIn(gloss.get("cefr"), {"B2", "C1", "chunk"})

    def test_b2_wohnen_question_includes_both_evidence_sentences(self):
        lesson = next(lesson for lesson in self.collection["lessons"] if lesson["id"] == "b2-wohnen")
        question = lesson["questions"][0]
        sentences = reader_sentences(lesson["text"])
        self.assertEqual(question["evidence_sentence_indices"], [2, 3])
        self.assertIn("klare Fragen zu sammeln", sentences[question["evidence_sentence_indices"][0]])
        self.assertIn("Entscheidung besser nachvollziehbar", sentences[question["evidence_sentence_indices"][1]])

    def test_b2_beruf_question_evidence_covers_kernarbeitszeit_context(self):
        lesson = next(lesson for lesson in self.collection["lessons"] if lesson["id"] == "b2-beruf")
        question = lesson["questions"][0]
        sentences = reader_sentences(lesson["text"])
        self.assertEqual(question["evidence_sentence_indices"], [4, 5])
        self.assertIn("Kernarbeitszeit", sentences[4])
        self.assertIn("Erreichbarkeit", sentences[5])

    def test_b2_plus_and_c1_lessons_include_inference_or_stance_questions(self):
        for lesson in self.collection["lessons"]:
            if lesson["level"] in {"B2+", "C1"}:
                with self.subTest(lesson=lesson["id"]):
                    self.assertTrue({q["type"] for q in lesson["questions"]} & {"推断", "立场"})

    def test_correct_choice_is_not_always_the_longest_option(self):
        questions = [q for lesson in self.collection["lessons"] for q in lesson["questions"] if len(q["options"]) > 2]
        shorter = sum(len(q["answer"]) < max(map(len, q["options"])) for q in questions)
        self.assertGreaterEqual(shorter, 5)

    def test_validator_rejects_insufficient_cefr_tags(self):
        collection = json.loads(json.dumps(self.collection))
        lesson = collection["lessons"][0]
        for gloss in lesson["glosses"][:5]:
            gloss.pop("cefr", None)
        errors = validate_collection(collection)
        self.assertTrue(any("requires at least 70%" in error for error in errors))

    def test_optional_stoplist_reports_matching_single_word_glosses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data" / "stoplist.txt").write_text("Hitzebelastung\n", encoding="utf-8")
            output = io.StringIO()
            with patch("validate_lessons.ROOT", root), contextlib.redirect_stdout(output):
                validate_collection(self.collection)
            self.assertIn("steht in der Stoppliste", output.getvalue())


if __name__ == "__main__":
    unittest.main()
