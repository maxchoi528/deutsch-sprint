#!/usr/bin/env python3
"""Optional browser smoke tests for the generated standalone pages."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import re
import sys
from threading import Thread


ROOT = Path(__file__).resolve().parents[1]
MARKER_RE = re.compile(r"\{([^{}|]+)\|([^{}|]+)\}")


def main():
    if importlib.util.find_spec("playwright") is None:
        print("SKIP: Playwright is not installed; browser smoke tests were not run.")
        return 0

    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            try:
                browser = playwright.chromium.launch(headless=True)
            except Exception as exc:
                print(f"SKIP: Playwright is installed, but Chromium is unavailable: {exc}")
                return 0
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            console_errors = []
            page.on("pageerror", lambda error: console_errors.append(str(error)))

            page.goto(f"{base_url}/p1-reader/index.html", wait_until="load")
            embedded = json.loads(page.locator("#lesson-data").text_content())
            lesson = embedded["lessons"][0]
            expected_paragraphs = sum(bool(p.strip()) for p in re.split(r"\n+", lesson["text"]))
            paragraphs = page.locator(".article-box .paragraph")
            assert paragraphs.count() == expected_paragraphs, (
                f"P1 paragraph count {paragraphs.count()} != {expected_paragraphs}"
            )

            first_marker = MARKER_RE.search(lesson["text"])
            assert first_marker, "The first lesson has no marked gloss"
            surface, gloss_id = first_marker.groups()
            gloss = next(g for g in lesson["glosses"] if g["id"] == gloss_id)
            word = page.locator(".gloss-word").first
            tooltip = page.locator(".gloss-pop").first
            assert not tooltip.is_visible(), "Gloss tooltip is visible before hover"
            word.hover()
            assert tooltip.is_visible(), "Gloss tooltip did not appear on hover"
            tooltip_text = tooltip.inner_text()
            for expected in (surface, gloss["lemma"], gloss["zh"], gloss["de_def"]):
                assert expected in tooltip_text, f"Tooltip is missing {expected!r}"

            page.select_option("#level-filter", "B2+")
            assert "Im hybriden Team klare Absprachen finden" in page.locator(".article-head").inner_text(), (
                "The B2+ filter did not select a B2+ lesson"
            )
            lesson = next(item for item in embedded["lessons"] if item["id"] == "b2-beruf")
            no_plural = next(gloss for gloss in lesson["glosses"] if gloss.get("plural_note"))
            gloss_button = page.locator(
                f'[aria-describedby^="tip-{no_plural["id"]}-"]'
            ).first
            gloss_button.hover()
            note_tooltip = page.locator("#" + gloss_button.get_attribute("aria-describedby"))
            assert "通常无复数" in note_tooltip.inner_text(), "plural_note was not shown in the tooltip"

            page.goto(f"{base_url}/p7-practice/index.html", wait_until="load")
            has_nested_blocks = page.evaluate(
                """() => {
                  const block = new Set(['DIV','SECTION','ARTICLE','ASIDE','NAV','HEADER','FOOTER','FIELDSET','UL','OL','DETAILS']);
                  return [...document.querySelectorAll('p')].some(p => [...p.children].some(c => block.has(c.tagName)));
                }"""
            )
            assert not has_nested_blocks, "P7 has a block element directly nested in a paragraph"
            assert not console_errors, "Browser errors: " + "; ".join(console_errors)
            browser.close()
            print("PASS: P1 gloss tooltip and paragraph structure; P7 paragraph nesting; no page errors.")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
