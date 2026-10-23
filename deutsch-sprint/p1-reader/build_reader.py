#!/usr/bin/env python3
"""Embed canonical lesson JSON into the standalone reader HTML."""

import json
from pathlib import Path
from validate_lessons import validate_file

ROOT = Path(__file__).resolve().parent
template = (ROOT / "reader.template.html").read_text(encoding="utf-8")
data = json.loads((ROOT / "lessons.json").read_text(encoding="utf-8"))
errors = validate_file(ROOT / "lessons.json")
if errors:
    raise SystemExit("课件校验失败：\n- " + "\n- ".join(errors))
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</script", "<\\/script")
output = template.replace("__LESSON_JSON__", payload)
(ROOT / "index.html").write_text(output, encoding="utf-8")
print(f"生成 {ROOT / 'index.html'}（{len(data['lessons'])} 篇课件）")
