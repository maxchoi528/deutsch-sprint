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
prompts = {
    "__P3_PROMPT_JSON__": json.dumps((ROOT / "p3-p4-prompts" / "speaking-coach.md").read_text(encoding="utf-8"), ensure_ascii=False),
    "__P4_PROMPT_JSON__": json.dumps((ROOT / "p3-p4-prompts" / "writing-coach.md").read_text(encoding="utf-8"), ensure_ascii=False),
}
replacements = {"__SYLLABUS_JSON__": payload, **prompts}
for marker, value in replacements.items():
    if template.count(marker) != 1:
        raise SystemExit(f"dashboard.template.html 必须恰好包含一个 {marker} 占位符")
    template = template.replace(marker, value)
(ROOT / "index.html").write_text(template, encoding="utf-8")
print(f"生成 {ROOT / 'index.html'}（{len(syllabus['weeks'])} 周计划）")
