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
        self.assertIn("Sprecherin A:", listening["transcript"])
        self.assertIn("Sprecher B:", listening["transcript"])
        labels = re.findall(r"^(Sprecherin A|Sprecher B):", listening["transcript"], re.M)
        self.assertTrue(all(left != right for left, right in zip(labels, labels[1:])), "dialogue should alternate speakers")
        sentences = reader_sentences(listening["transcript"])
        for question in listening["questions"]:
            with self.subTest(question=question["q"]):
                self.assertGreaterEqual(question["evidence_sentence_index"], 0)
                evidence = sentences[question["evidence_sentence_index"]]
                self.assertTrue(evidence.startswith("Sprecher"))

    def test_interview_and_lecture_formats_and_speaker_labels(self):
        listening = [section for section in self.exam["sections"] if section["kind"] == "listening"]
        self.assertGreaterEqual(len(listening), 3)
        interview = next(section for section in listening if "Interview" in section["title"])
        lecture = next(section for section in listening if "Kurzvortrag" in section["title"])
        self.assertIn("Sprecherin A:", interview["transcript"])
        self.assertIn("Sprecher B:", interview["transcript"])
        self.assertRegex(lecture["transcript"], r"Sprecher C:")
        self.assertNotIn("Gesprächspartnerin", " ".join(q["q"] for section in listening for q in section["questions"]))
        for section in listening:
            sentences = reader_sentences(section["transcript"])
            for question in section["questions"]:
                self.assertLess(question["evidence_sentence_index"], len(sentences), (section["id"], question["q"]))
        self.assertIn("单人讲座式", self.template)
        self.assertIn("没有两种可区分的德语系统语音", self.template)

    def test_official_durations_have_source_and_are_labeled_verified(self):
        self.assertIn("Durchfuehrungsbestimmungen_C1_neu.pdf", self.exam["source_note"])
        sections = {section["id"]: section for section in self.exam["sections"]}
        self.assertEqual(sections["lesen"]["official_duration_minutes"], 65)
        self.assertEqual(sections["hoeren"]["official_duration_minutes"], 40)
        self.assertEqual(sections["schreiben"]["official_duration_minutes"], 75)
        self.assertEqual(sections["sprechen"]["official_duration_minutes"], 20)
        self.assertIn("etwa 15 Minuten", sections["sprechen"]["source_note"])
        self.assertIn("已核实（以报考页为准）", self.template)
        self.assertNotIn("待核实", self.template)

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
