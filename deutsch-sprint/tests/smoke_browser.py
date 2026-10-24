#!/usr/bin/env python3
"""Optional browser smoke tests for the generated standalone pages."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import os
import json
from pathlib import Path
import re
import sys
from threading import Thread


ROOT = Path(__file__).resolve().parents[1]
MARKER_RE = re.compile(r"\{([^{}|]+)\|([^{}|]+)\}")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def skip_browser(reason):
    strict = os.environ.get("REQUIRE_BROWSER") == "1"
    print(f"{'FAIL' if strict else 'SKIP'}: {reason}")
    return 1 if strict else 0


def main():
    if importlib.util.find_spec("playwright") is None:
        return skip_browser("Playwright is not installed; browser smoke tests were not run.")

    handler = partial(QuietHandler, directory=str(ROOT))
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
                return skip_browser(f"Chromium could not launch; browser smoke tests were not run: {exc}")
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            console_errors = []
            page.on("pageerror", lambda error: console_errors.append(str(error)))

            fresh = browser.new_page(viewport={"width": 390, "height": 844})
            fresh.clock.install(time=__import__('datetime').datetime(2026, 10, 24, 12, 0, 0))
            fresh.goto(f"{base_url}/index.html", wait_until="load")
            assert fresh.locator("#start-date-dialog").is_visible(), "First use should request a start date"
            fresh.locator("#initial-start-date").fill("2026-10-23")
            fresh.get_by_role("button", name="开始使用").click()
            stored = fresh.evaluate("JSON.parse(localStorage.getItem('deutschSprint.dashboard.v1'))")
            assert stored["settings"]["w1Start"] == "2026-10-26", "Friday start should align W1 to Monday"
            fresh.locator('[data-view="review"]').click()
            assert "W0" in fresh.locator(".page-heading h2").inner_text()
            assert "10月23日 – 10月25日" in fresh.locator(".page-heading p").inner_text()
            fresh.clock.set_fixed_time(__import__('datetime').datetime(2026, 11, 1, 12, 0, 0))
            fresh.reload()
            assert "W1" in fresh.locator(".hero-bottom").inner_text(), "Sunday should remain in the Monday-started W1"
            # Saturday and Monday starts exercise the shortest and longest ordinary W0 ranges.
            for start, expected in [
                ("2026-10-24", "2026-10-26"),
                ("2026-10-26", "2026-11-02"),
            ]:
                fresh.evaluate("localStorage.removeItem('deutschSprint.dashboard.v1')")
                fresh.reload()
                fresh.locator("#initial-start-date").fill(start)
                fresh.get_by_role("button", name="开始使用").click()
                stored = fresh.evaluate("JSON.parse(localStorage.getItem('deutschSprint.dashboard.v1'))")
                assert stored["settings"]["w1Start"] == expected
                from datetime import date as date_class
                w0_days = (date_class.fromisoformat(expected)-date_class.fromisoformat(start)).days
                assert w0_days == (2 if start == "2026-10-24" else 7)
            fresh.close()

            page.goto(f"{base_url}/p1-reader/index.html", wait_until="load")
            embedded = json.loads(page.locator("#lesson-data").text_content())
            active_id = page.locator("[data-lesson][aria-current=page]").get_attribute("data-lesson")
            lesson = next(l for l in embedded["lessons"] if l["id"] == active_id)
            assert lesson["level"] == "B2", "New learners should start with B2"
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
                """(() => {
                  if (!location.pathname.endsWith('/p7-practice/index.html') || sessionStorage.p7Seeded) return;
                  sessionStorage.p7Seeded = 'yes';
                  localStorage.setItem('deutschSprint.p7.v1', JSON.stringify({
                    currentId: 'schreiben-forum',
                    attempts: {
                      'schreiben-forum': {response: 'Alter Forumsentwurf'},
                      'schreiben-email': {response: 'Alter E-Mail-Entwurf'}
                    }
                  }));
                })();"""
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
            durations.nth(1).dispatch_event("change")
            assert page.locator("#timer").inner_text() == "75:00", "Custom per-task durations should be shown before starting"
            page.get_by_role("button", name="开始限时练习").click()
            assert "任务 1/2" in page.locator(".timer-label").inner_text()

            page.add_init_script(
                """(() => {
                  if (location.pathname !== '/index.html' || sessionStorage.p6Seeded) return;
                  sessionStorage.p6Seeded = 'yes';
                  const d = new Date();
                  const date = [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-');
                  localStorage.setItem('deutschSprint.dashboard.v1', JSON.stringify({
                    schemaVersion: 1, exportedAt: '2000-01-01T00:00:00.000Z',
                    settings: {startDate: date, theme: 'system'},
                    checkins: {[date]: {blocks: {}, newChunks: 2, retention: null, note: 'legacy'}},
                    gates: {w4: [true,true,true,true,true], w9: [true,true,true,true], w13: [true,true,true]},
                    mocks: [], errors: [{id:'legacy-error',date,type:'词序',original:'falsch',correction:'richtig',rule:'test'}]
                  }));
                })();"""
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
            assert migrated["schemaVersion"] == 3, "Legacy backup was not migrated"
            legacy_w1 = page.evaluate("d=>{const x=new Date(d+'T12:00:00');x.setDate(x.getDate()+3);return [x.getFullYear(),String(x.getMonth()+1).padStart(2,'0'),String(x.getDate()).padStart(2,'0')].join('-')}", migrated["settings"]["startDate"])
            assert migrated["settings"]["w1Start"] == legacy_w1, f"Legacy start+3 W1 anchor should be preserved: {migrated['settings']['w1Start']} != {legacy_w1}"
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
                  state.settings.startDate=key(start); const w1=new Date(start);w1.setDate(w1.getDate()+3);state.settings.w1Start=key(w1);
                  state.checkins=checkins; state.gates={w4:{},w9:{},w13:{}};
                  localStorage.setItem('deutschSprint.dashboard.v1',JSON.stringify(state));
                }"""
            )
            page.reload(wait_until="load")
            page.get_by_role("button", name="周复盘").click()
            hours_rule = page.locator(".rule-item", has_text="本周主动学习少于 30 小时")
            assert hours_rule.locator(".tag").inner_text() == "已触发", "A week with five recorded days should evaluate the low-hours rule"
            assert not console_errors, "Browser errors: " + "; ".join(console_errors)
            from browser_flows import extra_flows, shadow_flow, reader_flow
            extra_flows(browser, base_url, console_errors)
            shadow_flow(browser, base_url, console_errors)
            reader_flow(browser, console_errors)
            assert not console_errors, "Browser errors: " + "; ".join(console_errors)
            browser.close()
            print("PASS: P1 gloss tooltip and paragraph structure; P6 first-use date, Monday-aligned W1, legacy migration and five-day review; P7 paragraph nesting; no page errors.")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        import traceback
        traceback.print_exc()
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
