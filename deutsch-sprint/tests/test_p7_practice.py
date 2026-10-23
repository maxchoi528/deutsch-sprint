import json
from pathlib import Path
import re
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def reader_sentences(text):
    return [
        sentence.strip()
        for paragraph in re.split(r"\n+", text)
        for sentence in re.split(r"(?<=[.!?。！？])\s+(?=[„A-ZÄÖÜ])", paragraph.strip())
        if sentence.strip()
    ]


class P7PracticeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exam = json.loads((PROJECT_ROOT / "p7-practice" / "exam.json").read_text(encoding="utf-8"))
        cls.template = (PROJECT_ROOT / "p7-practice" / "template.html").read_text(encoding="utf-8")

    def test_small_reading_and_listening_practice_durations_are_explicit(self):
        reading = next(section for section in self.exam["sections"] if section["kind"] == "reading")
        listening = next(section for section in self.exam["sections"] if section["kind"] == "listening")
        self.assertEqual((reading["duration_minutes"], reading["official_duration_minutes"]), (20, 65))
        self.assertEqual((listening["duration_minutes"], listening["official_duration_minutes"]), (15, 40))

    def test_listening_is_a_dialogue_with_valid_evidence_indices(self):
        listening = next(section for section in self.exam["sections"] if section["kind"] == "listening")
        self.assertIn("Sprecher A:", listening["transcript"])
        self.assertIn("Sprecher B:", listening["transcript"])
        sentences = reader_sentences(listening["transcript"])
        for question in listening["questions"]:
            with self.subTest(question=question["q"]):
                self.assertGreaterEqual(question["evidence_sentence_index"], 0)
                evidence = sentences[question["evidence_sentence_index"]]
                self.assertTrue(evidence.startswith("Sprecher"))

    def test_writing_has_one_shared_module_and_preserves_legacy_draft_migration(self):
        writing = [section for section in self.exam["sections"] if section["kind"] == "writing"]
        self.assertEqual(len(writing), 1)
        self.assertEqual(writing[0]["duration_minutes"], 75)
        self.assertEqual(len(writing[0]["tasks"]), 2)
        self.assertEqual(writing[0]["official_duration_minutes"], 75)
        self.assertIn("schreiben-forum", self.template)
        self.assertIn("schreiben-email", self.template)
        self.assertIn("legacyDraftMigrated", self.template)
        self.assertIn("data-writing-custom", self.template)
        self.assertIn("data-writing-duration", self.template)


if __name__ == "__main__":
    unittest.main()
