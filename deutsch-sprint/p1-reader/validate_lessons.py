#!/usr/bin/env python3
"""Validate P1 lesson glosses and evidence using the reader's sentence rules."""

import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MARKER_RE = re.compile(r"\{([^{}|]+)\|([^{}|]+)\}")
# Gloss markup is presentation-only; allow one marked word at a sentence start
# while preserving the reader's punctuation and paragraph rules.
SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.!?。！？])\s+(?=[{„A-ZÄÖÜ])"
)
WORD_RE = re.compile(r"\S+")


def reader_sentences(text):
    """Mirror reader.template.html: split nonempty paragraphs, then sentences."""
    result = []
    for paragraph in re.split(r"\n+", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        result.extend(
            sentence.strip()
            for sentence in SENTENCE_SPLIT_RE.split(paragraph)
            if sentence.strip()
        )
    return result


def validate_collection(collection):
    errors = []
    lessons = collection.get("lessons") if isinstance(collection, dict) else None
    if not isinstance(lessons, list) or not lessons:
        return ["collection must contain a nonempty 'lessons' array"]

    for lesson in lessons:
        lesson_id = lesson.get("id", "<unknown>")
        text = lesson.get("text", "")
        if not isinstance(text, str):
            errors.append(f"{lesson_id}: text must be a string")
            continue

        glosses = lesson.get("glosses", [])
        gloss_ids = [g.get("id") for g in glosses if isinstance(g, dict)]
        if len(gloss_ids) != len(set(gloss_ids)):
            errors.append(f"{lesson_id}: gloss ids must be unique")
        gloss_id_set = set(gloss_ids)
        counts = {gloss_id: 0 for gloss_id in gloss_id_set}
        for surface, gloss_id in MARKER_RE.findall(text):
            if gloss_id not in gloss_id_set:
                errors.append(f"{lesson_id}: marker {{{surface}|{gloss_id}}} has no gloss")
            else:
                counts[gloss_id] += 1
        for gloss_id, count in counts.items():
            if count == 0:
                errors.append(f"{lesson_id}: gloss {gloss_id!r} is not marked in the text")

        words = len(WORD_RE.findall(MARKER_RE.sub(r"\1", text)))
        required_glosses = max(12, math.ceil(words * 0.05))
        if len(gloss_ids) < required_glosses:
            errors.append(
                f"{lesson_id}: has {len(gloss_ids)} glosses for {words} words; "
                f"requires at least {required_glosses} (12 and 5% density)"
            )

        sentences = reader_sentences(text)
        for question_index, question in enumerate(lesson.get("questions", []), start=1):
            answer = question.get("answer")
            options = question.get("options", [])
            if answer not in options:
                errors.append(f"{lesson_id}: question {question_index} answer is not in options")
            evidence_index = question.get("evidence_sentence_index")
            if not isinstance(evidence_index, int) or isinstance(evidence_index, bool):
                errors.append(f"{lesson_id}: question {question_index} evidence index must be an integer")
                continue
            if not 0 <= evidence_index < len(sentences):
                errors.append(
                    f"{lesson_id}: question {question_index} evidence index {evidence_index} "
                    f"is outside 0..{len(sentences) - 1}"
                )
                continue
            evidence = MARKER_RE.sub(r"\1", sentences[evidence_index])
            print(f"[{lesson_id} Q{question_index} · sentence {evidence_index}] {evidence}")

    return errors


def validate_file(path=ROOT / "lessons.json"):
    try:
        collection = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read lesson JSON: {exc}"]
    return validate_collection(collection)


def main():
    errors = validate_file()
    if errors:
        print("Lesson validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Lesson validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
