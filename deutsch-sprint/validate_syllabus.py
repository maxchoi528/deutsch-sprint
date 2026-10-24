#!/usr/bin/env python3
"""Validate the weekly plan against its checked-in schema constraints."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "syllabus.json"
SCHEMA = ROOT / "syllabus.schema.json"
BLOCKS = {"anki", "deep", "speaking", "listening", "writing"}


def validate():
    try:
        data = json.loads(DATA.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        lessons = json.loads((ROOT / "p1-reader" / "lessons.json").read_text(encoding="utf-8"))["lessons"]
        lesson_ids = {lesson["id"] for lesson in lessons}
    except (OSError, json.JSONDecodeError, KeyError) as exc:
        return [f"无法读取计划、schema 或课件：{exc}"]

    issues = []
    if schema.get("properties", {}).get("schemaVersion", {}).get("const") != 1:
        issues.append("syllabus schemaVersion schema 必须为 1")
    if data.get("schemaVersion") != 1:
        issues.append("syllabus.json schemaVersion 必须为 1")
    weeks = data.get("weeks")
    if not isinstance(weeks, list) or len(weeks) != 16:
        return issues + ["weeks 必须是 16 周数组"]
    for expected, week in enumerate(weeks, 1):
        prefix = f"W{expected}"
        if not isinstance(week, dict):
            issues.append(f"{prefix} 必须是对象")
            continue
        if week.get("week") != expected:
            issues.append(f"{prefix} 编号缺失或顺序错误")
        for field in ("grammar_theme", "reading_lesson_id", "speaking_topic", "writing_task_type", "review_points"):
            if not isinstance(week.get(field), str) or not week[field].strip():
                issues.append(f"{prefix}.{field} 必须是非空文本")
        if week.get("stage") not in {"A", "B", "C", "D"}:
            issues.append(f"{prefix}.stage 必须是 A/B/C/D")
        if week.get("reading_lesson_id") not in lesson_ids:
            issues.append(f"{prefix} 推荐课件不存在：{week.get('reading_lesson_id')}")
        tasks = week.get("daily_tasks")
        if not isinstance(tasks, dict) or set(tasks) != BLOCKS:
            issues.append(f"{prefix}.daily_tasks 必须恰好覆盖五个学习块：{', '.join(sorted(BLOCKS))}")
        elif any(not isinstance(tasks[key], str) or not tasks[key].strip() for key in BLOCKS):
            issues.append(f"{prefix}.daily_tasks 含空任务")
    return issues


if __name__ == "__main__":
    errors = validate()
    if errors:
        for issue in errors:
            print(f"ERROR: {issue}", file=sys.stderr)
        raise SystemExit(1)
    print("syllabus.json 通过 16 周与 schema 约束检查。")
