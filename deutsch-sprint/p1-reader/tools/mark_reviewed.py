#!/usr/bin/env python3
"""Record a tutor's review on a lesson and rebuild the reader page."""
import argparse
from datetime import date
import json
import re
import subprocess
import sys
from pathlib import Path

READER = Path(__file__).resolve().parents[1]
ROOT = READER.parent


def mark_reviewed(collection: dict, lesson_id: str, tutor: str, reviewed_at: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed_at):
        raise ValueError("日期格式必须为 YYYY-MM-DD")
    date.fromisoformat(reviewed_at)
    lesson = next((item for item in collection.get("lessons", []) if item.get("id") == lesson_id), None)
    if lesson is None:
        return False
    lesson["review_status"] = "tutor-reviewed"
    lesson["reviewed_by"] = tutor.strip()
    lesson["reviewed_at"] = reviewed_at
    return True


def main():
    parser = argparse.ArgumentParser(description="记录导师抽检姓名和日期，并重建 P1")
    parser.add_argument("lesson_id")
    parser.add_argument("--tutor", required=True, help="导师姓名或署名")
    parser.add_argument("--date", default=date.today().isoformat(), help="抽检日期 YYYY-MM-DD；默认今天")
    args = parser.parse_args()
    if not args.tutor.strip():
        parser.error("--tutor 不能为空")
    path = READER / "lessons.json"
    original = path.read_bytes()
    try:
        collection = json.loads(original)
        changed = mark_reviewed(collection, args.lesson_id, args.tutor, args.date)
    except (json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"无法记录抽检：{exc}")
    if not changed:
        raise SystemExit(f"未找到课件 id：{args.lesson_id}")
    path.write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = subprocess.run([sys.executable, str(READER / "build_reader.py")], cwd=ROOT)
    if result.returncode:
        path.write_bytes(original)
        raise SystemExit("构建失败，已恢复 lessons.json。")
    print(f"已记录 {args.lesson_id}：导师 {args.tutor.strip()} · {args.date}")


if __name__ == "__main__":
    main()
