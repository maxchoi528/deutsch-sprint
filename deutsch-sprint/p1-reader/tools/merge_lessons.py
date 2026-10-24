#!/usr/bin/env python3
"""Validate and merge an AI-authored lesson file, then regenerate the reader."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

READER = Path(__file__).resolve().parents[1]
ROOT = READER.parent
sys.path.insert(0, str(READER))
from validate_lessons import validate_file, validate_collection  # noqa: E402


def load_lessons(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        lessons = value
    elif isinstance(value, dict) and isinstance(value.get("lessons"), list):
        lessons = value["lessons"]
    else:
        lessons = [value]
    return lessons


def merge_into(collection: dict, additions: list) -> list[str]:
    existing = collection.get("lessons", [])
    errors = []
    known = {lesson.get("id") for lesson in existing}
    for lesson in additions:
        lesson_id = lesson.get("id")
        if not lesson_id or lesson_id in known:
            errors.append(f"lesson id 缺失或已存在：{lesson_id!r}")
        if lesson.get("source") == "user-provided":
            errors.append(f"{lesson_id}: 用户提供的原文只应放在 p1-reader/local/，不会合并到被跟踪的课件集合")
        if lesson.get("source") != "original-ai":
            errors.append(f"{lesson_id}: 合并工具只接受 source=original-ai 的新原创课件")
        if not lesson.get("grammar_target"):
            errors.append(f"{lesson_id}: 缺少 grammar_target")
        if lesson.get("review_status") != "ai-generated-unreviewed":
            errors.append(f"{lesson_id}: 新课件 review_status 必须为 ai-generated-unreviewed")
        known.add(lesson_id)
    if errors:
        return errors
    candidate = {**collection, "lessons": existing + additions}
    errors = validate_collection(candidate)
    if errors:
        return errors
    collection["lessons"] = existing + additions
    return []


def main():
    parser = argparse.ArgumentParser(description="校验原创新课件、合并到 lessons.json 并重建 P1")
    parser.add_argument("lesson_file", type=Path, help="单篇、数组或 lesson 集合 JSON")
    args = parser.parse_args()
    errors = validate_file(args.lesson_file)
    if errors:
        raise SystemExit("新课件校验失败：\n- " + "\n- ".join(errors))
    try:
        additions = load_lessons(args.lesson_file)
        source_path = READER / "lessons.json"
        original_bytes = source_path.read_bytes()
        collection = json.loads(original_bytes)
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        raise SystemExit(f"无法读取课件文件：{exc}")
    errors = merge_into(collection, additions)
    if errors:
        raise SystemExit("无法合并：\n- " + "\n- ".join(errors))
    source_path.write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(READER / "build_reader.py")], cwd=ROOT)
    if result.returncode:
        source_path.write_bytes(original_bytes)
        raise SystemExit("构建失败，已恢复 lessons.json。")
    print(f"已合并 {len(additions)} 篇原创课件并重建 P1。")


if __name__ == "__main__":
    main()
