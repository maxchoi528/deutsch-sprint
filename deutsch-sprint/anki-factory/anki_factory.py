#!/usr/bin/env python3
"""Build Anki-ready CSV files from Deutsch Sprint reading lessons and error logs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


MARKER_RE = re.compile(r"\{([^{}|]+)\|([^{}|]+)\}")
SENTENCE_RE = re.compile(r"[^.!?。！？]+[.!?。！？]*", re.S)
VALID_TYPES = ("cloze", "definition", "collocation", "error")


@dataclass(frozen=True)
class Note:
    kind: str
    front: str
    back: str
    source: str

    @property
    def key(self) -> str:
        raw = "\0".join((self.kind, self.front, self.back, self.source))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def source_name(data: dict[str, Any], path: Path) -> str:
    return clean(data.get("source_id") or data.get("source") or data.get("title") or path.stem)


def strip_markers(text: str) -> str:
    return MARKER_RE.sub(lambda m: m.group(1), text)


def sentence_notes(text: str, glosses: list[dict[str, Any]], source: str) -> list[Note]:
    gloss_ids = {clean(g.get("id")) for g in glosses if clean(g.get("id"))}
    notes: list[Note] = []
    for raw_sentence in SENTENCE_RE.findall(text):
        sentence = raw_sentence.strip()
        matches = list(MARKER_RE.finditer(sentence))
        if not matches:
            continue
        marked = [m for m in matches if clean(m.group(2)) in gloss_ids]
        if not marked:
            continue
        # One target per note makes the number of generated Cloze cards match
        # the number of marked word blocks, even when a sentence has two glosses.
        for target in marked:
            clozed = []
            for match in MARKER_RE.finditer(sentence):
                surface = clean(match.group(1))
                clozed.append(
                    "{{c1::%s}}" % surface if match.start() == target.start() else surface
                )
            pieces = []
            cursor = 0
            for match, replacement in zip(MARKER_RE.finditer(sentence), clozed):
                pieces.extend((sentence[cursor:match.start()], replacement))
                cursor = match.end()
            pieces.append(sentence[cursor:])
            front = re.sub(r"\s+", " ", "".join(pieces)).strip()
            notes.append(Note("cloze", front, f"Quelle: {source}", source))
    return notes


def word_answer(gloss: dict[str, Any]) -> str:
    surface = clean(gloss.get("surface"))
    lemma = clean(gloss.get("lemma")) or surface
    article = clean(gloss.get("article"))
    plural = clean(gloss.get("plural"))
    word = lemma
    if article and not re.match(r"^(der|die|das|ein|eine|den|dem|des)\s", lemma, re.I):
        word = f"{article} {lemma}"
    elif article and re.match(r"^(der|die|das)\s", lemma, re.I):
        word = lemma
    elif surface and not lemma:
        word = surface
    extras = []
    if plural:
        if re.match(r"^(die|meist|ohne)\s", plural, re.I):
            plural_form = f"Plural: {plural}"
        else:
            plural_form = f"Plural: die {plural.removeprefix('Plural:').strip()}"
        extras.append(plural_form)
    elif clean(gloss.get("plural_note")):
        extras.append(clean(gloss["plural_note"]))
    zh = clean(gloss.get("zh"))
    if zh:
        extras.append(zh)
    return word + (f" ({'; '.join(extras)})" if extras else "")


def definition_notes(glosses: list[dict[str, Any]], source: str) -> list[Note]:
    notes = []
    for gloss in glosses:
        definition = clean(gloss.get("de_def"))
        answer = word_answer(gloss)
        if definition and answer:
            notes.append(Note("definition", definition, f"{answer}\nQuelle: {source}", source))
    return notes


def collocation_items(raw: Any) -> Iterable[tuple[str, str]]:
    if isinstance(raw, dict):
        prompt = clean(raw.get("prompt"))
        answer = clean(raw.get("answer"))
        if prompt and answer:
            yield prompt, answer
        return
    if not isinstance(raw, str):
        return
    for separator in ("→", "=>", "::"):
        if separator in raw:
            prompt, answer = raw.split(separator, 1)
            if clean(prompt) and clean(answer):
                yield clean(prompt), clean(answer)
            return


def collocation_notes(glosses: list[dict[str, Any]], source: str, warnings: list[str]) -> list[Note]:
    notes = []
    for gloss in glosses:
        for raw in gloss.get("collocations", []) or []:
            for prompt, answer in collocation_items(raw):
                notes.append(Note("collocation", prompt, f"{answer}\nQuelle: {source}", source))
            if isinstance(raw, str) and not any(sep in raw for sep in ("→", "=>", "::")):
                warnings.append(f"搭配“{clean(raw)}”缺少 prompt/answer，已跳过；可改为 {{\"prompt\":\"… ___\",\"answer\":\"…\"}}。")
    return notes


def normalize_error(item: dict[str, Any], fallback_source: str) -> Note | None:
    original = clean(item.get("original") or item.get("front"))
    correction = clean(item.get("correction"))
    rule = clean(item.get("rule"))
    back = item.get("back")
    if isinstance(back, dict):
        correction = clean(back.get("correct") or back.get("correction")) or correction
        rule = clean(back.get("rule")) or rule
    elif isinstance(back, str):
        correction = correction or clean(back)
    front = original or clean(item.get("meaning"))
    if not front or not correction or not rule:
        return None
    src = clean(item.get("date"))
    nested_source = item.get("source")
    if isinstance(nested_source, dict):
        src = clean(nested_source.get("date") or nested_source.get("id")) or src
    elif isinstance(nested_source, str):
        src = clean(nested_source) or src
    src = src or fallback_source
    return Note("error", front, f"{correction}\n规则：{rule}\nQuelle: {src}", src)


def extract_errors(data: Any, fallback_source: str, warnings: list[str]) -> list[Note]:
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("errors"), list):
        items = data["errors"]
    elif isinstance(data, dict):
        items = [data]
    else:
        warnings.append(f"错误日志格式不支持：{fallback_source}")
        return []
    notes = []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            warnings.append(f"{fallback_source} 第 {index} 条错误记录不是对象，已跳过。")
            continue
        note = normalize_error(item, fallback_source)
        if note:
            notes.append(note)
        else:
            warnings.append(f"{fallback_source} 第 {index} 条缺少原句、修正或规则，已跳过。")
    return notes


def lesson_notes(data: dict[str, Any], path: Path, warnings: list[str]) -> list[Note]:
    source = source_name(data, path)
    glosses = data.get("glosses") if isinstance(data.get("glosses"), list) else []
    glosses = [g for g in glosses if isinstance(g, dict)]
    text = clean(data.get("text"))
    notes = sentence_notes(text, glosses, source)
    notes.extend(definition_notes(glosses, source))
    notes.extend(collocation_notes(glosses, source, warnings))
    if not notes:
        warnings.append(f"{path.name} 没有生成卡片；检查 text 标记、glosses 和搭配格式。")
    return notes


def unmarked_glosses(data: Any) -> list[dict[str, str]]:
    """List lesson glosses with no matching in-text id marker."""
    if not isinstance(data, dict) or not isinstance(data.get("glosses"), list):
        return []
    marked = {clean(gloss_id) for _, gloss_id in MARKER_RE.findall(clean(data.get("text")))}
    result = []
    for gloss in data["glosses"]:
        if not isinstance(gloss, dict):
            continue
        gloss_id = clean(gloss.get("id"))
        if gloss_id and gloss_id not in marked:
            result.append({
                "id": gloss_id,
                "surface": clean(gloss.get("surface")),
                "lemma": clean(gloss.get("lemma")),
            })
    return result


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 {path}: {exc}") from exc


def unique_notes(notes: list[Note]) -> tuple[list[Note], int]:
    seen: set[str] = set()
    unique: list[Note] = []
    removed = 0
    for note in notes:
        if note.key in seen:
            removed += 1
        else:
            seen.add(note.key)
            unique.append(note)
    return unique, removed


def write_csv(path: Path, headers: tuple[str, str], rows: list[Note]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        writer.writerow(headers)
        for note in rows:
            writer.writerow((note.front, note.back))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="将 Deutsch Sprint 精读 JSON 和错误日志生成 Anki CSV 文件。"
    )
    parser.add_argument("inputs", nargs="+", help="P1 课件 JSON 或仪表盘导出的 JSON 备份")
    parser.add_argument("--output", "-o", type=Path, default=Path("anki-export"), help="CSV 输出目录（默认：./anki-export）")
    parser.add_argument("--stats", action="store_true", help="列出各类卡片数量和未标记词条")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output: Path = args.output
    all_notes: dict[str, list[Note]] = {kind: [] for kind in VALID_TYPES}
    warnings: list[str] = []
    unmarked: list[tuple[str, dict[str, str]]] = []
    for name in args.inputs:
        path = Path(name)
        try:
            data = read_json(path)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        # P1 exports a single lesson, an array, or a {lessons: [...]} collection.
        if isinstance(data, dict) and "lessons" in data:
            if not isinstance(data["lessons"], list) or not data["lessons"]:
                print(f"{path.name}: lessons 必须为非空课件数组。", file=sys.stderr)
                return 2
            items = data["lessons"]
        elif isinstance(data, list) and any(isinstance(item, dict) and ("glosses" in item or "text" in item) for item in data):
            items = data
        else:
            items = [data]
        for item in items:
            if isinstance(item, dict) and ("glosses" in item or "text" in item):
                unmarked.extend((source_name(item, path), gloss) for gloss in unmarked_glosses(item))
                notes = lesson_notes(item, path, warnings)
            else:
                notes = extract_errors(item, path.stem, warnings)
            for note in notes:
                all_notes[note.kind].append(note)

    try:
        output.mkdir(parents=True, exist_ok=True)
        duplicates = 0
        for kind in VALID_TYPES:
            all_notes[kind], removed = unique_notes(all_notes[kind])
            duplicates += removed
            if kind == "cloze":
                headers = ("Text", "Extra")
                filename = "01-cloze.csv"
            else:
                headers = ("Front", "Back")
                filename = {"definition":"02-definitions.csv", "collocation":"03-collocations.csv", "error":"04-errors.csv"}[kind]
            write_csv(output / filename, headers, all_notes[kind])
    except OSError as exc:
        print(f"无法写入输出目录 {output}: {exc}", file=sys.stderr)
        return 2

    total = sum(len(rows) for rows in all_notes.values())
    print(f"完成：{total} 张卡，去重 {duplicates} 条 → {output.resolve()}")
    for kind, rows in all_notes.items():
        print(f"  {kind:12s} {len(rows):4d}")
    if args.stats:
        print("统计：")
        for kind, rows in all_notes.items():
            print(f"  {kind}: {len(rows)}")
        print("未被标记、因此未生成 cloze 的 gloss：")
        if unmarked:
            for source, gloss in unmarked:
                label = gloss["surface"] or gloss["lemma"] or "（无词面）"
                print(f"  {source} · {gloss['id']} · {label}")
        else:
            print("  无")
    for warning in warnings:
        print(f"提示：{warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
