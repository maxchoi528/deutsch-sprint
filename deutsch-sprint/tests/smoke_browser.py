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

            page.add_init_script(
                """() => {
                  if (!location.pathname.endsWith('/p7-practice/index.html')) return;
                  localStorage.setItem('deutschSprint.p7.v1', JSON.stringify({
                    currentId: 'schreiben-forum',
                    attempts: {
                      'schreiben-forum': {response: 'Alter Forumsentwurf'},
                      'schreiben-email': {response: 'Alter E-Mail-Entwurf'}
                    }
                  }));
                }"""
            )
            page.goto(f"{base_url}/p7-practice/index.html", wait_until="load")
            legacy_p7 = page.evaluate("JSON.parse(localStorage.getItem('deutschSprint.p7.v1'))")
            migrated_writing = legacy_p7["attempts"]["schreiben"]
            assert migrated_writing["responses"]["forum"] == "Alter Forumsentwurf"
            assert migrated_writing["responses"]["email"] == "Alter E-Mail-Entwurf"
            assert migrated_writing["legacyDraftMigrated"] is True
            assert "75" in page.locator(".timer-label").inner_text(), "Writing tasks should share a 75-minute timer"
            assert page.locator('[data-task="schreiben"]').count() == 1, "Writing must be one shared module"
            page.locator('[data-task="lesen"]').click()
            assert "缩小版练习，不是整套模考" in page.locator(".lede").inner_text()
            has_nested_blocks = page.evaluate(
                """() => {
                  const block = new Set(['DIV','SECTION','ARTICLE','ASIDE','NAV','HEADER','FOOTER','FIELDSET','UL','OL','DETAILS']);
                  return [...document.querySelectorAll('p')].some(p => [...p.children].some(c => block.has(c.tagName)));
                }"""
            )
            assert not has_nested_blocks, "P7 has a block element directly nested in a paragraph"
            page.locator('[data-task="schreiben"]').click()
            page.locator('[data-writing-custom]').check()
            durations = page.locator('[data-writing-duration]')
            assert durations.count() == 2, "Custom writing mode should expose two task timers"
            durations.nth(0).fill("30")
            durations.nth(1).fill("45")
            assert page.locator("#timer").inner_text() == "75:00", "Custom per-task durations should be shown before starting"
            page.get_by_role("button", name="开始限时练习").click()
            assert "任务 1/2" in page.locator(".timer-label").inner_text()

            page.add_init_script(
                """() => {
                  if (location.pathname !== '/index.html') return;
                  const d = new Date();
                  const date = [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-');
                  localStorage.setItem('deutschSprint.dashboard.v1', JSON.stringify({
                    schemaVersion: 1, exportedAt: '2000-01-01T00:00:00.000Z',
                    settings: {startDate: date, theme: 'system'},
                    checkins: {[date]: {blocks: {}, newChunks: 2, retention: null, note: 'legacy'}},
                    gates: {w4: [true,true,true,true,true], w9: [true,true,true,true], w13: [true,true,true]},
                    mocks: [], errors: [{id:'legacy-error',date,type:'词序',original:'falsch',correction:'richtig',rule:'test'}]
                  }));
                }"""
            )
            page.goto(f"{base_url}/index.html", wait_until="load")
            assert page.locator(".backup-reminder.is-stale").count() == 1, "Old export timestamp should trigger the backup reminder"
            page.get_by_role("button", name="周复盘").click()
            assert "W0" in page.locator(".page-heading h2").inner_text(), "Review did not use the diagnostic W0 label"
            statuses = page.locator(".rule-item .tag").all_inner_texts()
            assert statuses and all(status == "待观察" for status in statuses), f"W0 rules should all be pending: {statuses}"
            assert page.locator('[data-gate-field="w4.reading"]').count() == 1
            assert page.locator('[data-gate-field="w13.mock1.title"]').count() == 1
            migrated = page.evaluate("JSON.parse(localStorage.getItem('deutschSprint.dashboard.v1'))")
            assert migrated["schemaVersion"] == 2, "Legacy backup was not migrated"
            assert migrated["checkins"] and migrated["errors"][0]["id"] == "legacy-error", "Legacy progress was lost"
            assert isinstance(migrated["gates"]["w4"], dict), "Legacy checkbox gates should be safely ignored"
            assert migrated["lastExportAt"].startswith("2000-01-01"), "Legacy export timestamp was not migrated"

            page.evaluate(
                """() => {
                  const today = new Date();
                  const key = d => [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-');
                  const start = new Date(today); start.setDate(start.getDate()-21);
                  const checkins = {};
                  for (let i=0;i<5;i++) { const d=new Date(today); d.setDate(d.getDate()-i); checkins[key(d)]={blocks:{},newChunks:0,retention:null,note:''}; }
                  const state=JSON.parse(localStorage.getItem('deutschSprint.dashboard.v1'));
                  state.settings.startDate=key(start); state.checkins=checkins; state.gates={w4:{},w9:{},w13:{}};
                  localStorage.setItem('deutschSprint.dashboard.v1',JSON.stringify(state));
                }"""
            )
            page.reload(wait_until="load")
            page.get_by_role("button", name="周复盘").click()
            hours_rule = page.locator(".rule-item", has_text="本周主动学习少于 30 小时")
            assert hours_rule.locator(".tag").inner_text() == "已触发", "A week with five recorded days should evaluate the low-hours rule"
            assert not console_errors, "Browser errors: " + "; ".join(console_errors)
            browser.close()
            print("PASS: P1 gloss tooltip and paragraph structure; P6 W0, migration and five-day review; P7 paragraph nesting; no page errors.")
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
