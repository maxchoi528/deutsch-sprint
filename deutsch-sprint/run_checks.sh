#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

python3 p1-reader/validate_lessons.py
python3 validate_syllabus.py
python3 build_dashboard.py
python3 p1-reader/build_reader.py
python3 p7-practice/build.py
python3 -m unittest discover -s tests
python3 tests/smoke_browser.py
