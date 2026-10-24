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
VALID_CEFR = {"B2", "C1", "chunk"}
STYLE_PATTERNS = re.compile(r"\bsollte man\b|\bkann sinnvoll\b|\bhilft\b|\bhilfreich\b|\bkann helfen\b", re.I)


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
        tagged = [g.get("cefr") for g in glosses if isinstance(g, dict) and g.get("cefr") in VALID_CEFR]
        invalid_cefr = [g.get("id", "<unknown>") for g in glosses if isinstance(g, dict) and g.get("cefr") and g.get("cefr") not in VALID_CEFR]
        if invalid_cefr:
            errors.append(f"{lesson_id}: gloss cefr must be B2, C1 or chunk: {', '.join(invalid_cefr)}")
        if glosses and len(tagged) / len(glosses) < 0.70:
            errors.append(f"{lesson_id}: only {len(tagged)}/{len(glosses)} glosses have B2/C1/chunk tags; requires at least 70%")
        stoplist = ROOT / "data" / "stoplist.txt"
        if stoplist.is_file():
            blocked = {line.strip().casefold() for line in stoplist.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")}
            for gloss in glosses:
                if not isinstance(gloss, dict) or gloss.get("pos", "").casefold() not in {"nomen", "verb", "adjektiv", "adverb"}:
                    continue
                lemma = re.sub(r"^(der|die|das|ein|eine)\s+", "", str(gloss.get("lemma", "")), flags=re.I).casefold()
                if lemma in blocked:
                    print(f"WARNUNG [{lesson_id}]: Gloss {gloss.get('id')} „{lemma}“ steht in der Stoppliste.")
        words = len(WORD_RE.findall(MARKER_RE.sub(r"\1", text)))
        tokens = MARKER_RE.sub(r"\1", text).split()
        for offset in range(0, max(1, len(tokens)), 200):
            section = " ".join(tokens[offset:offset+200])
            style_count = len(STYLE_PATTERNS.findall(section))
            if style_count > 3:
                print(f"WARNUNG [{lesson_id}]: {style_count} typische Ratgeber-Phrasen innerhalb von höchstens 200 Wörtern; bitte gegenlesen.")
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

        required_glosses = max(12, math.ceil(words * 0.05))
        if len(gloss_ids) < required_glosses:
            errors.append(
                f"{lesson_id}: has {len(gloss_ids)} glosses for {words} words; "
                f"requires at least {required_glosses} (12 and 5% density)"
            )

        sentences = reader_sentences(text)
        question_types = set()
        for question_index, question in enumerate(lesson.get("questions", []), start=1):
            question_types.add(question.get("type"))
            if question.get("type") not in {"对错", "选择", "配对", "选择（细节）", "推断", "立场"}:
                errors.append(f"{lesson_id}: question {question_index} has an unsupported type")
            answer = question.get("answer")
            options = question.get("options", [])
            if answer not in options:
                errors.append(f"{lesson_id}: question {question_index} answer is not in options")
            indices = question.get("evidence_sentence_indices")
            if indices is None:
                indices = [question.get("evidence_sentence_index")]
            if not isinstance(indices, list) or not indices:
                errors.append(f"{lesson_id}: question {question_index} evidence indices must be a nonempty array")
                continue
            if all(isinstance(index, int) and not isinstance(index, bool) for index in indices) and len(indices) != len(set(indices)):
                errors.append(f"{lesson_id}: question {question_index} evidence indices must be unique")
            for evidence_index in indices:
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
        if lesson.get("level") in {"B2+", "C1"} and not question_types.intersection({"推断", "立场"}):
            errors.append(f"{lesson_id}: B2+/C1 lessons need at least one inference or stance question")

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
