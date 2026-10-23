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
    assert value['schemaVersion'] == 2 and value['mocks'][0]['scores']['reading'] == 76
    assert value['checkins'][today]['note'] == 'old note'
    assert value['gates']['w4']['reading'] is None
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
    assert exported['schemaVersion'] == 2 and exported['errors'][0]['id'] == 'old-error'
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
    page.close()

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
