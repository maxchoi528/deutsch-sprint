#!/usr/bin/env python3
"""Generate a standalone practice page with embedded JSON exercises."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
template = (ROOT / "template.html").read_text(encoding="utf-8")
content = json.loads((ROOT / "exam.json").read_text(encoding="utf-8"))
payload = json.dumps(content, ensure_ascii=False, separators=(",", ":")).replace("</script", "<\\/script")
(ROOT / "index.html").write_text(template.replace("__EXAM_JSON__", payload), encoding="utf-8")
print(f"生成 {ROOT / 'index.html'}（{len(content['sections'])} 个练习模块）")
