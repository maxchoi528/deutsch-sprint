import contextlib
import io
import json
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
