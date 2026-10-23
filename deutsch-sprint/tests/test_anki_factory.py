import contextlib
import io
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "anki-factory"))
import anki_factory as factory  # noqa: E402


class AnkiFactoryTests(unittest.TestCase):
    def test_cloze_notes_have_at_most_two_blanks(self):
        glosses = [{"id": f"g{i}"} for i in range(1, 4)]
        notes = factory.sentence_notes(
            "{eins|g1} und {zwei|g2} sowie {drei|g3} bleiben im Satz.",
            glosses,
            "test",
        )
        self.assertEqual(len(notes), 3)
        for note in notes:
            self.assertLessEqual(len(re.findall(r"\{\{c\d+::", note.front)), 2)

    def test_full_lesson_collection_generates_all_marked_clozes(self):
        collection = json.loads((PROJECT_ROOT / "p1-reader/lessons.json").read_text())
        notes, marked = [], 0
        for lesson in collection["lessons"]:
            marked += len(re.findall(r"\{[^{}|]+\|[^{}|]+\}", lesson["text"]))
            notes.extend(factory.sentence_notes(lesson["text"], lesson["glosses"], lesson["id"]))
        unique, _ = factory.unique_notes(notes)
        self.assertGreaterEqual(len(unique), marked)

    def test_duplicate_notes_are_removed(self):
        note = factory.Note("error", "falsch", "richtig", "test")
        unique, removed = factory.unique_notes([note, note])
        self.assertEqual(unique, [note])
        self.assertEqual(removed, 1)

    def test_reads_errors_from_dashboard_export_shape(self):
        export = {
            "schemaVersion": 1,
            "settings": {"startDate": "2026-10-23"},
            "checkins": {},
            "gates": {},
            "mocks": [],
            "errors": [{
                "date": "2026-10-25",
                "type": "词序",
                "original": "Heute ich lerne Deutsch.",
                "correction": "Heute lerne ich Deutsch.",
                "rule": "主句变位动词位于第二位。",
            }],
        }
        warnings = []
        notes = factory.extract_errors(export, "dashboard", warnings)
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].kind, "error")
        self.assertEqual(notes[0].front, "Heute ich lerne Deutsch.")
        self.assertIn("Heute lerne ich Deutsch.", notes[0].back)
        self.assertEqual(warnings, [])

    def test_missing_error_fields_produce_actionable_warning(self):
        warnings = []
        notes = factory.extract_errors(
            {"errors": [{"original": "Heute ich lerne Deutsch."}]},
            "dashboard",
            warnings,
        )
        self.assertEqual(notes, [])
        self.assertTrue(any("缺少原句、修正或规则" in warning for warning in warnings))

    def test_plural_note_appears_on_definition_card(self):
        answer = factory.word_answer({
            "surface": "Erreichbarkeit",
            "lemma": "Erreichbarkeit",
            "article": "die",
            "plural": "",
            "plural_note": "通常无复数",
            "zh": "可联系性",
        })
        self.assertIn("通常无复数", answer)

    def test_stats_lists_counts_and_unmarked_glosses_and_csv_keeps_bom(self):
        lesson = {
            "source_id": "stats-test",
            "text": "Eine {Markierung|g1} ist hier.",
            "glosses": [
                {"id": "g1", "surface": "Markierung", "lemma": "Markierung", "article": "die", "plural": "", "zh": "标记", "de_def": "Ein Zeichen."},
                {"id": "g2", "surface": "Fehlt", "lemma": "Fehlen", "article": "das", "plural": "", "zh": "缺少", "de_def": "Nicht vorhanden sein."},
            ],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_path = root / "lesson.json"
            input_path.write_text(json.dumps(lesson, ensure_ascii=False), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = factory.main([str(input_path), "--output", str(root / "cards"), "--stats"])
            self.assertEqual(result, 0)
            self.assertIn("cloze: 1", output.getvalue())
            self.assertIn("stats-test · g2 · Fehlt", output.getvalue())
            csv_path = root / "cards" / "01-cloze.csv"
            self.assertTrue(csv_path.read_bytes().startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
