#!/usr/bin/env python3
"""Embed the validated weekly syllabus into the standalone P6 dashboard."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
from validate_syllabus import validate

issues = validate()
if issues:
    raise SystemExit("\n".join(issues))
template = (ROOT / "dashboard.template.html").read_text(encoding="utf-8")
syllabus = json.loads((ROOT / "syllabus.json").read_text(encoding="utf-8"))
payload = json.dumps(syllabus, ensure_ascii=False, separators=(",", ":")).replace("</script", "<\\/script")
if template.count("__SYLLABUS_JSON__") != 1:
    raise SystemExit("dashboard.template.html 必须恰好包含一个 syllabus 占位符")
(ROOT / "index.html").write_text(template.replace("__SYLLABUS_JSON__", payload), encoding="utf-8")
print(f"生成 {ROOT / 'index.html'}（{len(syllabus['weeks'])} 周计划）")
