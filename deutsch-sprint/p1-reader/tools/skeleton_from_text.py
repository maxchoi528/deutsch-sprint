#!/usr/bin/env python3
"""Turn supplied text into a sentence-indexed lesson skeleton (not ready to merge)."""
import argparse
import json
import re
import sys
from pathlib import Path

SPLIT = re.compile(r"(?<=[.!?。！？])\s+(?=[{„A-ZÄÖÜ])")
WORD = re.compile(r"\S+")
MARKER = re.compile(r"\{([^{}|]+)\|([^{}|]+)\}")


def make_skeleton(text: str, lesson_id: str, title: str, level: str, genre: str):
    paragraphs = [part.strip() for part in re.split(r"\n+", text) if part.strip()]
    sentences = [sentence.strip() for paragraph in paragraphs for sentence in SPLIT.split(paragraph) if sentence.strip()]
    count = len(WORD.findall(MARKER.sub(r"\1", text)))
    return {
        "id": lesson_id,
        "title": title,
        "level": level,
        "genre": genre,
        "grammar_target": "",
        "source": "user-provided",
        "text": text,
        "word_count": count,
        "sentences": [{"index": index, "text": sentence} for index, sentence in enumerate(sentences)],
        "glosses": [],
        "questions": [],
        "summary_zh": "",
        "grammar_focus": [],
        "recycled_words": [],
        "review_status": "ai-generated-unreviewed",
    }


def main():
    parser = argparse.ArgumentParser(description="将正文转为带切句与词数统计的 P1 lesson 骨架")
    parser.add_argument("text_file", type=Path, help="UTF-8 正文文件")
    parser.add_argument("--id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--level", choices=("B2", "B2+", "C1"), default="B2")
    parser.add_argument("--genre", default="Informationstext")
    parser.add_argument("--output", type=Path, help="输出 JSON；省略时写到标准输出")
    args = parser.parse_args()
    try:
        text = args.text_file.read_text(encoding="utf-8")
    except OSError as exc:
        parser.error(f"无法读取正文：{exc}")
    skeleton = make_skeleton(text, args.id, args.title, args.level, args.genre)
    output = json.dumps(skeleton, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
