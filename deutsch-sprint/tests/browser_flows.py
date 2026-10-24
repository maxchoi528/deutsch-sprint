"""Browser interaction checks; invoked by smoke_browser.py, no real user data."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
P6 = 'deutschSprint.dashboard.v1'
P7 = 'deutschSprint.p7.v1'


def saved(page, key):
    return page.evaluate('(key) => JSON.parse(localStorage.getItem(key))', key)


def seed(page, key, value):
    page.evaluate('([key,value]) => localStorage.setItem(key,JSON.stringify(value))', [key, value])
    page.reload()


def edit(page, selector, value):
    page.locator(selector).fill(str(value))
    page.locator(selector).dispatch_event('change')


def extra_flows(browser, base_url, errors):
    page = browser.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base_url + '/index.html')
    today = page.evaluate("new Date().toLocaleDateString('sv-SE')")
    legacy = dict(schemaVersion=1, exportedAt='2000-01-01T00:00:00.000Z',
                  settings=dict(startDate=today, theme='system'),
                  checkins={today: dict(blocks={'anki': dict(done=True, minutes=45)}, newChunks=8, retention=90, note='old note')},
                  gates={'w4': [True]*5, 'w9': [True]*4, 'w13': [True]*3},
                  mocks=[dict(id='old-mock', date=today, title='B2 baseline', mode='single', scores={'reading': 76, 'listening': 72})],
                  errors=[dict(id='old-error', date=today, type='词序', original='Heute ich lerne.', correction='Heute lerne ich.', rule='V2')])
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('#import-file').set_input_files(dict(name='legacy.json', mimeType='application/json', buffer=json.dumps(legacy).encode()))
    page.wait_for_function("JSON.parse(localStorage.getItem('deutschSprint.dashboard.v1')||'{}').errors?.[0]?.id === 'old-error'")
    value = saved(page, P6)
    assert value['schemaVersion'] == 3 and value['settings']['w1Start'] == (page.evaluate("d=>{const x=new Date(d+'T12:00:00');x.setDate(x.getDate()+3);return x.toLocaleDateString('sv-SE')}", today))
    assert value['mocks'][0]['scores']['reading'] == 76
    assert value['checkins'][today]['note'] == 'old note'
    assert value['gates']['w4']['reading'] is None
    assert page.locator('[data-syllabus-task]').count() == 5
    assert 'b2-wohnen' in page.locator('.syllabus-panel a').get_attribute('href')
    page.locator('[data-syllabus-task="anki"]').check()
    assert saved(page, P6)['checkins'][today]['dailyTasks']['anki'] is True
    page.reload()
    assert page.locator('[data-syllabus-task="anki"]').is_checked()
    edit(page, '[data-block-minutes="anki"]', 50)
    page.reload()
    assert page.locator('[data-block-minutes="anki"]').input_value() == '50'
    page.locator('[data-view="review"]').click()
    for gate, score, level in [('w4', 75, 'B2 稳定'), ('w9', 60, '接近 C1')]:
        for skill in ['reading', 'listening']:
            edit(page, f'[data-gate-field="{gate}.{skill}"]', score)
        if gate == 'w4':
            edit(page, '[data-gate-field="w4.retention"]', 85)
        for skill in ['writing', 'speaking']:
            page.select_option(f'[data-gate-field="{gate}.{skill}.level"]', level)
            page.select_option(f'[data-gate-field="{gate}.{skill}.evaluator"]', '导师')
            edit(page, f'[data-gate-field="{gate}.{skill}.date"]', today)
        card = page.locator('.gate-card').filter(has=page.locator(f'[data-gate-field="{gate}.reading"]'))
        assert '已达标' in card.locator('h3').inner_text()
        edit(page, f'[data-gate-field="{gate}.reading"]', score-1)
        assert '未达标' in card.locator('h3').inner_text()
        edit(page, f'[data-gate-field="{gate}.reading"]', score)
    with page.expect_download() as download_info:
        page.locator('[data-action="export"]').first.click()
    exported = json.loads(Path(download_info.value.path()).read_text())
    assert exported['schemaVersion'] == 3 and exported['errors'][0]['id'] == 'old-error'
    assert exported['lastExportAt'] == exported['exportedAt']
    assert not page.locator('.backup-reminder.is-stale').count()
    sys.path.insert(0, str(ROOT / 'anki-factory'))
    import anki_factory
    warnings = []
    cards = anki_factory.extract_errors(exported, 'browser-export', warnings)
    assert len(cards) == 1 and not warnings
    print('PASS: P6 actual legacy JSON file import, daily persistence, W4/W9 boundaries, JSON download -> Anki.')

    # W0/W1 transitions and three states, using isolated synthetic records.
    for offset, days, minutes, expected_week, expected_status in [
        (2, 3, 0, 0, '待观察'), (3, 0, 0, 1, '待观察'),
        (6, 4, 0, 1, '待观察'), (7, 5, 0, 1, '已触发'),
        (7, 5, 360, 1, '未触发'), (10, 0, 0, 2, '待观察')]:
        value = page.evaluate('''([offset,days,minutes]) => {
          const key=d=>d.toLocaleDateString('sv-SE');
          const state=JSON.parse(localStorage.getItem('deutschSprint.dashboard.v1'));
          const start=new Date();start.setDate(start.getDate()-offset);state.settings.startDate=key(start);
          const oldW1=new Date(start);oldW1.setDate(oldW1.getDate()+3);state.settings.w1Start=key(oldW1);
          state.checkins={};
          for(let i=0;i<days;i++){const d=new Date();d.setDate(d.getDate()-i);
            state.checkins[key(d)]={blocks:{anki:{done:true,minutes}},retention:null,newChunks:0,note:''};}
          return state;
        }''', [offset, days, minutes])
        seed(page, P6, value)
        page.locator('[data-view="review"]').click()
        assert f'W{expected_week}' in page.locator('.page-heading h2').inner_text()
        rule = page.locator('.rule-item', has_text='本周主动学习少于 30 小时')
        assert rule.locator('.tag').inner_text() == expected_status
    # Ended W1 with fewer than five records is evaluated; empty history stays pending.
    value = saved(page, P6)
    value['checkins'] = {value['settings']['startDate']: legacy['checkins'][today]}
    seed(page, P6, value)
    page.locator('[data-view="review"]').click()
    page.select_option('#review-week', '1')
    rule = page.locator('.rule-item', has_text='本周主动学习少于 30 小时')
    assert rule.locator('.tag').inner_text() == '待观察'
    previous_day = page.evaluate("() => { const d=new Date();d.setDate(d.getDate()-1);return d.toLocaleDateString('sv-SE'); }")
    value['checkins'][previous_day] = legacy['checkins'][today]
    seed(page, P6, value)
    page.locator('[data-view="review"]').click()
    page.select_option('#review-week', '1')
    assert rule.locator('.tag').inner_text() == '已触发'
    page.select_option('#review-week', '0')
    assert all(s == '待观察' for s in page.locator('.rule-item .tag').all_inner_texts())
    # W13 needs two complete, dated sets AND certificate acceptance confirmation.
    for index, date in [(1, previous_day), (2, today)]:
        prefix=f'w13.mock{index}'
        edit(page, f'[data-gate-field="{prefix}.title"]', f'Full set {index}')
        edit(page, f'[data-gate-field="{prefix}.date"]', date)
        for skill in ['reading', 'listening']:
            edit(page, f'[data-gate-field="{prefix}.{skill}"]', 70)
        for skill in ['writing', 'speaking']:
            page.select_option(f'[data-gate-field="{prefix}.{skill}.level"]', '接近 C1')
            page.select_option(f'[data-gate-field="{prefix}.{skill}.evaluator"]', '导师')
            edit(page, f'[data-gate-field="{prefix}.{skill}.date"]', date)
    gate = page.locator('.gate-card').filter(has=page.locator('[data-gate-field="w13.siteConfirmed"]'))
    assert '待评估' in gate.locator('h3').inner_text()
    page.locator('[data-gate-field="w13.siteConfirmed"]').check()
    assert '已达标' in gate.locator('h3').inner_text()
    edit(page, '[data-gate-field="w13.mock2.listening"]', 69)
    assert '未达标' in gate.locator('h3').inner_text()
    print('PASS: P6 W0/W1/W2, all three rule states, ended-week selection, W13 two-set gate.')
    page.close()

    page = browser.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base_url + '/p7-practice/index.html')
    seed(page, P7, {'currentId': 'schreiben-forum', 'attempts': {
        'schreiben-forum': {'response': 'Legacy forum'}, 'schreiben-email': {'response': 'Legacy email'}}})
    page.locator('[data-action="start"]').click()
    first = saved(page, P7)['attempts']['schreiben']
    assert first['expiresAt'] - first['startedAt'] == 75*60000
    page.locator('#writing-response').fill('Mein erster Text.')
    page.locator('[data-writing-task-index="1"]').click()
    page.locator('#writing-response').fill('Meine zweite Aufgabe.')
    page.reload()
    assert saved(page, P7)['attempts']['schreiben']['expiresAt'] == first['expiresAt']
    assert page.locator('#writing-response').input_value() == 'Meine zweite Aufgabe.'
    page.locator('[data-writing-task-index="0"]').click()
    assert page.locator('#writing-response').input_value() == 'Mein erster Text.'
    state = saved(page, P7)
    state['attempts']['schreiben']['expiresAt'] = 1
    seed(page, P7, state)
    assert saved(page, P7)['attempts']['schreiben']['timedOut']
    assert page.locator('#writing-response').is_disabled()
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('[data-action="reset"]').click()
    page.reload()
    page.locator('[data-action="start"]').click()
    assert page.locator('#writing-response').input_value() == '', 'Reset resurrected a legacy draft'
    page.locator('[data-action="submit"]').click()
    page.once('dialog', lambda dialog: dialog.accept())
    page.locator('[data-action="reset"]').click()
    page.locator('[data-writing-custom]').check()
    edit(page, '[data-writing-duration="0"]', 2)
    edit(page, '[data-writing-duration="1"]', 3)
    assert page.locator('#timer').inner_text() == '05:00', 'Custom total did not refresh'
    page.locator('[data-action="start"]').click()
    state = saved(page, P7)
    now = page.evaluate('Date.now()')
    state['attempts']['schreiben']['taskTimers'][0]['expiresAt'] = now - 60000
    seed(page, P7, state)
    current = saved(page, P7)['attempts']['schreiben']
    assert current['activeTaskIndex'] == 1
    assert current['taskTimers'][1]['expiresAt'] == now + 120000, 'Reload granted extra custom time'
    state = saved(page, P7)
    state['attempts']['schreiben']['taskTimers'][1]['expiresAt'] = 1
    seed(page, P7, state)
    assert saved(page, P7)['attempts']['schreiben']['timedOut']
    print('PASS: P7 shared deadline, both drafts, reload, expiry, reset, custom totals and elapsed time.')
    page.locator('[data-task="hoeren-interview"]').click()
    assert '40 分钟' in page.locator('.nav-item[aria-current="page"]').inner_text()
    assert '双人对话/访谈' in page.locator('.panel .help').first.inner_text()
    page.locator('[data-task="hoeren-vortrag"]').click()
    assert '单人讲座式' in page.locator('.panel .help').first.inner_text()
    page.locator('[data-task="sprechen"]').click()
    assert '配对口试' in page.locator('.notice').inner_text()
    assert 'etwa 20 Minuten' in page.locator('.notice').inner_text()
    print('PASS: P7 verified exam duration labels, interview, lecture-style listening and paired-speaking guidance.')
    page.close()

    page = browser.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base_url + '/p1-reader/index.html?lesson=b2-wohnen')
    assert page.locator('.article-head h2').inner_text() == 'Eine Wohnung finden, ohne sofort zuzuschlagen'
    page.close()
    print('PASS: P6 weekly syllabus checklist persistence and direct link to the selected P1 lesson.')

    mobile_dashboard = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    mobile_dashboard.add_init_script("""(() => { const d=new Date();const key=d.toLocaleDateString('sv-SE');localStorage.setItem('deutschSprint.dashboard.v1',JSON.stringify({schemaVersion:3,settings:{startDate:key,w1Start:key,theme:'light'},checkins:{},gates:{w4:{},w9:{},w13:{}},mocks:[],errors:[]})); })();""")
    mobile_dashboard.goto(base_url + '/index.html')
    assert mobile_dashboard.locator('[data-syllabus-task]').count() == 5
    assert mobile_dashboard.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'P6 syllabus overflows a mobile viewport'
    mobile_dashboard.close()
    print('PASS: P6 weekly plan remains usable without horizontal overflow at mobile width.')

    error_page = browser.new_page()
    error_page.add_init_script("""(() => { const d=new Date();const key=d.toLocaleDateString('sv-SE');localStorage.setItem('deutschSprint.dashboard.v1',JSON.stringify({schemaVersion:3,settings:{startDate:key,w1Start:key,theme:'light'},checkins:{},gates:{w4:{},w9:{},w13:{}},mocks:[],errors:[]})); })();""")
    error_page.goto(base_url + '/index.html')
    error_page.locator('[data-view="errors"]').click()
    error_page.locator('#error-import-text').fill('| 类型 | 我的原句 | 修正 | 一句话规则 |\n| --- | --- | --- | --- |\n| 词序 | Heute ich lerne. | Heute lerne ich. | 主句变位动词通常放在第二位。 |\n| 词序 | Heute ich lerne. | Heute lerne ich. | 主句变位动词通常放在第二位。 |')
    error_page.locator('[data-action="preview-error-import"]').click()
    assert '1 条新记录，1 条重复记录' in error_page.locator('#error-import-status').inner_text()
    error_page.locator('[data-action="import-errors"]').click()
    assert len(saved(error_page, P6)['errors']) == 1, 'Markdown import should deduplicate repeated rows'
    error_page.locator('#error-import-text').fill('类型\t我的原句\t修正\t一句话规则\n词序\tHeute ich lerne.\tHeute lerne ich.\t主句变位动词通常放在第二位。')
    error_page.locator('[data-action="preview-error-import"]').click()
    assert '0 条新记录，1 条重复记录' in error_page.locator('#error-import-status').inner_text()
    error_page.context.grant_permissions(['clipboard-read', 'clipboard-write'], origin=base_url)
    expected_prompt = (ROOT / 'p3-p4-prompts/speaking-coach.md').read_text(encoding='utf-8')
    error_page.locator('[data-copy-prompt="speaking"]').click()
    error_page.wait_for_function('navigator.clipboard.readText().then(text => text.length > 0)')
    assert error_page.evaluate('navigator.clipboard.readText()') == expected_prompt
    expected_prompt = (ROOT / 'p3-p4-prompts/writing-coach.md').read_text(encoding='utf-8')
    error_page.locator('[data-copy-prompt="writing"]').click()
    error_page.wait_for_function('navigator.clipboard.readText().then(text => text.length > 0)')
    assert error_page.evaluate('navigator.clipboard.readText()') == expected_prompt
    print('PASS: P6 Markdown/TSV error import preview, deduplication and exact P3/P4 prompt copy.')
    error_page.close()

    mobile = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    page = mobile.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((ROOT / 'p1-reader/index.html').as_uri())
    assert page.locator('.gloss-pop:visible').count() == 0
    page.locator('.gloss-word').first.tap()
    assert page.locator('.gloss-pop:visible').count() == 1
    bounds = page.locator('.gloss-pop:visible').bounding_box()
    assert bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= 391
    page.locator('h1').tap()
    assert page.locator('.gloss-pop:visible').count() == 0, 'Mobile tooltip did not dismiss'
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    print('PASS: P1 direct file:// use, mobile tap tooltip, dismissal and viewport containment.')
    mobile.close()


def shadow_flow(browser, base_url, errors):
    """Exercise manual dictation and audio UI with synthetic audio / stub ASR only."""
    import io
    import wave
    with io.BytesIO() as buffer:
        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(8000)
            wav.writeframes(b'\0\0' * 8000 * 6)
        audio = buffer.getvalue()
    page = browser.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.add_init_script('''(() => {
      navigator.mediaDevices.getUserMedia = async () => {
        window.testAudioContext = new AudioContext();
        return window.testAudioContext.createMediaStreamDestination().stream;
      };
    })();''')
    page.goto(base_url + '/p5-shadow/index.html')
    page.locator('#reference').fill('Heute lernen wir gemeinsam. Morgen üben wir weiter.')
    page.locator('#reference').press('Tab')
    assert page.locator('.sentence-card').count() == 2
    assert page.locator('[data-play="0"]').is_disabled()
    page.locator('[data-dictation="0"]').fill('Heute lernen wir.')
    page.locator('[data-compare="0"]').click()
    assert 'gemeinsam' in page.locator('#missed-list').inner_text(), str((page.locator('#missed-list').inner_text(), page.locator('#diff-0').inner_text(), errors))
    with page.expect_download() as info:
        page.locator('#export-missed').click()
    lesson = json.loads(Path(info.value.path()).read_text())
    import anki_factory
    notes = anki_factory.sentence_notes(lesson['text'], lesson['glosses'], 'p5-browser')
    assert len(notes) == 1
    page.locator('#audio-file').set_input_files(dict(name='silence.wav', mimeType='audio/wav', buffer=audio))
    page.wait_for_function("document.querySelector('#audio').readyState >= 1")
    page.route('**/api/transcribe', lambda route: route.fulfill(json={
        'language': 'de', 'duration': 6,
        'segments': [{'start': 1, 'end': 2, 'text': 'Heute lernen wir gemeinsam.'},
                     {'start': 3, 'end': 4, 'text': 'Morgen üben wir weiter.'}]}))
    page.locator('#transcribe').click()
    page.wait_for_function("!document.querySelector('[data-loop]').disabled")
    page.locator('[data-loop="0"]').click()
    position = page.evaluate("() => { const a=document.querySelector('#audio');a.currentTime=2.1;a.dispatchEvent(new Event('timeupdate'));return a.currentTime; }")
    assert 1 <= position < 1.3, 'Sentence loop stopped instead of repeating'
    page.locator('#stop-loop').click()
    assert page.locator('#audio').evaluate('(a) => a.paused')
    # Recording ASR must not replace source-audio timestamps or reference material.
    page.unroute('**/api/transcribe')
    page.route('**/api/transcribe', lambda route: route.fulfill(json={
        'language': 'de', 'duration': 1,
        'segments': [{'start': 0, 'end': 1, 'text': 'Heute lernen wir.'}]}))
    page.locator('#record-start').click()
    page.locator('#record-stop').click()
    page.locator('#shadow-result').wait_for(state='visible')
    assert page.locator('.sentence-card').count() == 2
    assert '1.0–2.0' in page.locator('.sentence-time').first.inner_text()
    assert 'gemeinsam' in page.locator('#shadow-result').inner_text()
    print('PASS: P5 manual dictation -> Anki; synthetic-audio loop; stub-ASR recording preserves source timestamps (no real ASR/mic test).')
    page.close()


def reader_flow(browser, errors):
    import re
    page = browser.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto((ROOT / 'p1-reader/index.html').as_uri())
    lessons = json.loads(page.locator('#lesson-data').text_content())['lessons']
    for lesson in lessons:
        page.locator(f'[data-lesson="{lesson["id"]}"]').click()
        assert page.locator('.article-box .paragraph').count() == len([p for p in re.split(r'\n+', lesson['text']) if p.strip()])
        assert page.locator('.gloss-word').count() == len(re.findall(r'\{[^{}|]+\|[^{}|]+\}', lesson['text']))
        page.locator('[data-action="summary"]').first.click()
        assert page.locator('.summary-text').inner_text() == lesson['summary_zh']
    lesson = next(l for l in lessons if l['id'] == 'b2-wohnen')
    page.locator('[data-lesson="b2-wohnen"]').click()
    page.locator('[data-action="blind"]').click()
    assert page.locator('.gloss-word').first.is_disabled()
    for i, question in enumerate(lesson['questions']):
        page.locator('.question').nth(i).get_by_role('radio', name=question['answer'], exact=True).check()
    page.locator('[data-action="submit-quiz"]').click()
    assert page.locator('.feedback.correct').count() == 3
    assert page.locator('.sentence.evidence').count() >= 2, 'Multi-sentence evidence was not highlighted'
    assert page.locator('.sentence.evidence[data-sentence-index="2"]').count() == 1
    assert page.locator('.sentence.evidence[data-sentence-index="3"]').count() == 1
    page.reload()
    progress = saved(page, 'deutschSprint.reader.v1')['progress']['b2-wohnen'][-1]
    assert progress['blind'] and progress['score'] == 3
    page.goto((ROOT / 'index.html').as_uri())
    if page.locator('#start-date-dialog').is_visible():
        page.locator('#initial-start-date').fill(page.evaluate("new Date().toLocaleDateString('sv-SE')"))
        page.get_by_role('button', name='开始使用').click()
    assert page.locator('[aria-label="学习工具入口"] a').count() == 7
    for href in page.locator('[aria-label="学习工具入口"] a').evaluate_all('(links)=>links.map(a=>a.getAttribute("href"))'):
        assert (ROOT / href).is_file()
    edit(page, '[data-block-minutes="anki"]', 25)
    page.reload()
    assert page.locator('[data-block-minutes="anki"]').input_value() == '25'
    page.goto((ROOT / 'p7-practice/index.html').as_uri())
    page.locator('[data-task="schreiben"]').click()
    page.locator('[data-action="start"]').click()
    deadline = saved(page, P7)['attempts']['schreiben']['expiresAt']
    page.reload()
    assert saved(page, P7)['attempts']['schreiben']['expiresAt'] == deadline
    print('PASS: all 10 P1 lessons, summaries and gloss counts; blind quiz persistence; P6/P7 direct file:// use and toolkit links.')
    page.close()
