"""Flyer Factory Card D acceptance: Spanish drafts with mocked AI only.

This check is called by ``check_factory.py``. Every HTTP(S) request is
intercepted, provider credentials are synthetic, and no real AI service is
contacted.
"""
from __future__ import annotations

import json
import re
import sys
import uuid


AI_KEY = 'cultureshyft.factory.ai.v1'
BRIEFS_KEY = 'cultureshyft.factory.briefs.v1'
DRAFT_KEY = 'cultureshyft.factory.draft.v1'
REVIEW_NOTE = 'Review before printing. Have someone who speaks Spanish check this translation.'
FAKE_KEY = 'sk-' + 'TEST' + 'FAKE' * 8
UNKNOWN_KEY = 'sk-' + 'UNKNOWN' + 'TEST' * 8
FLYER_FIELDS = ('headline', 'subheadline', 'body', 'cta')
SOCIAL_FIELDS = ('instagramCaption', 'facebookDescription')
PROVIDERS = {
    'gemini': ('gemini-3.6-flash', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent'),
    'openai': ('gpt-6-luna', 'https://api.openai.com/v1/chat/completions'),
    'claude': ('claude-haiku-5-5', 'https://api.anthropic.com/v1/messages'),
}


def _check_spanish(chrome, output_dir):
    checks = sys.modules.get('__main__')
    if not hasattr(checks, 'FACTORY_PAGE'):
        import check_factory as checks
    from playwright.sync_api import expect, sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    profile = checks.SCRATCH_DIR / f'spanish-{uuid.uuid4().hex}'
    profile.mkdir(parents=True)
    calls, console, errors, held = [], [], [], []
    mock = {'provider': 'gemini', 'mode': 'success', 'text': ''}

    source = {
        'headline': 'CultureShyft neighborhood night',
        'subheadline': 'Media made to move people.',
        'body': 'Jordan Lee has 25 tickets at 123 Main Street. Visit https://example.test/path.',
        'cta': 'Call today at 248-505-0050',
        'instagramCaption': 'Meet Jordan Lee at 123 Main Street. ¿Ready?',
        'facebookDescription': 'CultureShyft welcomes neighbors on October 24 at 2 PM.',
    }
    translated = {
        'headline': 'Noche del vecindario de CultureShyft',
        'subheadline': 'Media made to move people.',
        'body': 'Jordan Lee tiene 25 boletos en 123 Main Street. Visita https://example.test/path.',
        'cta': 'Llama hoy al 248-505-0050',
        'instagramCaption': 'Conoce a Jordan Lee en 123 Main Street. ¿Listos?',
        'facebookDescription': 'CultureShyft da la bienvenida a los vecinos el October 24 at 2 PM.',
    }
    unicode_result = {
        **translated,
        'headline': '¿Sueñas con una comunidad CultureShyft más unida?',
        'body': 'Niñas, niños y familias: reunión en 123 Main Street. Ven con Jordan Lee y 25 vecinos. https://example.test/path.',
        'cta': '¡Llama al 248-505-0050!',
        'instagramCaption': '¿Mañana? Sí. Cultura, conexión y niñez en 123 Main Street.',
        'facebookDescription': '¡Acompáñanos! CultureShyft reúne a la comunidad el October 24 at 2 PM.',
    }

    def provider_for(url):
        if 'googleapis.com' in url:
            return 'gemini'
        if 'anthropic.com' in url:
            return 'claude'
        return 'openai'

    def provider_response(provider, text):
        if provider == 'gemini':
            return {'candidates': [{'content': {'parts': [{'text': text}]}, 'finishReason': 'STOP'}]}
        if provider == 'claude':
            return {'content': [{'type': 'text', 'text': text}], 'stop_reason': 'end_turn'}
        return {'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}]}

    def route_request(route):
        request = route.request
        if not request.url.startswith(('http:', 'https:')):
            route.continue_()
            return
        provider = provider_for(request.url)
        try:
            body = request.post_data_json
        except Exception:
            body = request.post_data
        calls.append({'url': request.url, 'headers': request.headers,
                      'method': request.method, 'body': body, 'provider': provider})
        mode = mock['mode']
        if mode == 'hold':
            held.append((route, provider))
        elif isinstance(mode, int):
            route.fulfill(status=mode, content_type='application/json', body=json.dumps({
                'error': {'message': f'Credential rejected: {FAKE_KEY} {UNKNOWN_KEY}'}}))
        else:
            route.fulfill(json=provider_response(provider, mock['text']))

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            str(profile), executable_path=str(chrome), headless=True,
            viewport={'width': 1024, 'height': 1366}, accept_downloads=True,
            args=['--no-sandbox', '--disable-gpu', '--disable-background-networking',
                  '--disable-component-update', '--allow-file-access-from-files'])
        context.route('**/*', route_request)
        page = context.pages[0]
        page.on('console', lambda msg: console.append(msg.text))
        page.on('pageerror', lambda error: errors.append(str(error)))

        def ready():
            page.evaluate('() => window.factoryReady')

        def brief():
            return page.evaluate('() => factoryBrief.collect()')

        def form_values():
            return brief()['values']

        def choose(provider):
            mock.update(provider=provider, mode='success', text='')
            if not page.locator('#ai-settings-dialog').is_visible():
                page.locator('#open-ai-settings').click()
            page.locator('#ai-provider').select_option(provider)
            if provider in ('gemini', 'openai', 'claude'):
                page.locator('#ai-api-key').fill(FAKE_KEY)
            expect(page.locator('#ai-model')).to_have_value(PROVIDERS[provider][0])
            page.locator('#ai-save-settings').click()
            expect(page.locator('#ai-settings-dialog')).not_to_be_visible()

        def translate(result, mode='success'):
            mock.update(mode=mode, text=json.dumps(result, ensure_ascii=False) if not isinstance(result, str) else result)
            page.locator('#ai-spanish-button').click()

        def wait_done():
            expect(page.locator('#ai-spanish-button')).to_have_text('Spanish version', timeout=40000)

        def spanish_values():
            return {field: page.locator('#ai-spanish-' + field).input_value()
                    for field in (*FLYER_FIELDS, *SOCIAL_FIELDS)
                    if page.locator('#ai-spanish-' + field).count()}

        def set_post_fields(instagram, facebook):
            page.evaluate('''([instagram, facebook]) => {
              const first = document.getElementById('ai-instagram-caption');
              const second = document.getElementById('ai-facebook-description');
              first.value = instagram; second.value = facebook;
              first.dispatchEvent(new Event('input', {bubbles: true}));
              second.dispatchEvent(new Event('input', {bubbles: true}));
            }''', [instagram, facebook])

        def system_and_user(call):
            body = call['body']
            if call['provider'] == 'gemini':
                return (body['systemInstruction']['parts'][0]['text'],
                        body['contents'][0]['parts'][0]['text'])
            if call['provider'] == 'claude':
                return body['system'], body['messages'][0]['content']
            return body['messages'][0]['content'], body['messages'][1]['content']

        def validate_request(provider, call, expected_source):
            assert call['provider'] == provider
            assert call['method'] == 'POST'
            assert call['url'] == PROVIDERS[provider][1], call['url']
            assert FAKE_KEY not in call['url']
            headers, body = call['headers'], call['body']
            if provider == 'gemini':
                assert headers['x-goog-api-key'] == FAKE_KEY
                assert 'authorization' not in headers
                assert body['generationConfig']['responseMimeType'] == 'application/json'
                schema = body['generationConfig'].get('responseSchema')
                assert schema and set(schema['required']) == set(expected_source)
                assert set(schema['properties']) == set(expected_source)
            elif provider == 'claude':
                assert headers['x-api-key'] == FAKE_KEY
                assert headers['anthropic-version'] == '2023-06-01'
                assert headers['anthropic-dangerous-direct-browser-access'] == 'true'
            else:
                assert headers['authorization'] == 'Bearer ' + FAKE_KEY
                assert body['response_format']['type'] == 'json_object'
            system, user = system_and_user(call)
            voice = page.evaluate('factoryAI.BRAND_VOICE')
            assert voice and voice in system
            for rule in ('Spanish', 'JSON', 'CultureShyft', 'Media made to move people.',
                         'proper names', 'no exclamation marks in body'):
                assert rule.lower() in system.lower(), f'Missing Spanish instruction: {rule}'
            serialized = json.dumps(body, ensure_ascii=False)
            for value in expected_source.values():
                assert value in serialized, f'Translation source omitted: {value}'
            for private in ('October 24 at 2 PM — DO NOT SEND', 'Community Hall — DO NOT SEND',
                            'private-contact@example.test', 'https://private-qr.example/',
                            'PRIVATE CUSTOMER — DO NOT SEND', 'private-customer@example.test',
                            'data:image/'):
                assert private not in serialized, f'Out-of-scope field sent to provider: {private}'
            assert FAKE_KEY not in json.dumps(body)
            # The user payload itself must carry only the requested translatable
            # fields. Generic preservation instructions may still name dates.
            for key in expected_source:
                assert key in user
            for key in ('date', 'place', 'contact', 'qrUrl'):
                assert not re.search(rf'["\']{key}["\']\s*:', user)

        def non_ai_storage():
            return page.evaluate('''() => Object.fromEntries(Object.keys(localStorage)
              .filter(k => k !== 'cultureshyft.factory.ai.v1')
              .map(k => [k, localStorage.getItem(k)]))''')

        def leak_check(*secrets):
            visible = page.locator('body').text_content()
            preview = json.dumps(spanish_values(), ensure_ascii=False) if page.locator('#ai-spanish-preview').count() else ''
            persisted = json.dumps(non_ai_storage(), ensure_ascii=False)
            diagnostics = '\n'.join(console + errors)
            for secret in secrets:
                assert secret not in visible
                assert secret not in preview
                assert secret not in persisted
                assert secret not in diagnostics
            assert not errors, errors

        try:
            page.goto(checks.FACTORY_PAGE.as_uri())
            ready()
            assert not calls, 'AI requested on page load'
            page.locator('#ai-spanish-button').click()
            expect(page.locator('#ai-settings-dialog')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('#ai-settings-dialog')).not_to_be_visible()
            assert not calls, 'Unconfigured Spanish tap should only open settings'

            originals = {
                'headline': source['headline'], 'subheadline': source['subheadline'],
                'date': 'October 24 at 2 PM — DO NOT SEND',
                'place': 'Community Hall — DO NOT SEND',
                'body': source['body'], 'cta': source['cta'],
                'contact': 'private-contact@example.test',
                'qr-url': 'https://private-qr.example/',
            }
            for field, value in originals.items():
                page.locator('#' + field).fill(value)
            page.locator('.order-details').evaluate('element => { element.open = true; }')
            page.locator('#clientName').fill('PRIVATE CUSTOMER — DO NOT SEND')
            page.locator('#clientEmail').fill('private-customer@example.test')
            page.locator('#extraSizes').select_option('3')
            page.locator('#accent').check()
            page.evaluate('''() => {
              const canvas = document.createElement('canvas'); canvas.width = canvas.height = 2;
              window.factoryPhoto.setState({dataUrl: canvas.toDataURL('image/png'), zoom: 1.4, focusX: .25, focusY: .75});
            }''')
            set_post_fields(source['instagramCaption'], source['facebookDescription'])
            page.wait_for_timeout(400)
            page.locator('#save-brief').click()
            english_form = brief()
            page.wait_for_function("JSON.parse(localStorage.getItem('cultureshyft.factory.draft.v1')).payload.values.headline.includes('CultureShyft')")
            english_draft = page.evaluate('(k) => localStorage.getItem(k)', DRAFT_KEY)
            english_library = json.loads(page.evaluate('(k) => localStorage.getItem(k)', BRIEFS_KEY))
            assert len(english_library) == 1
            call_count = len(calls)
            for field in originals:
                page.locator('#' + field).press('End')
            assert len(calls) == call_count, 'Typing or saving caused an AI request'

            for provider in PROVIDERS:
                choose(provider)
                call_count = len(calls)
                translate(translated)
                wait_done()
                assert len(calls) == call_count + 1, 'Spanish version must use one request'
                validate_request(provider, calls[-1], source)
                assert brief() == english_form, 'Translation preview changed the English form'
                assert page.evaluate('(k) => localStorage.getItem(k)', DRAFT_KEY) == english_draft
                expect(page.locator('#ai-spanish-preview')).to_be_visible()
                expect(page.locator('#ai-spanish-review-note')).to_have_text(REVIEW_NOTE)
                for field, value in translated.items():
                    expect(page.locator('#ai-spanish-' + field)).to_have_value(value)
                    expect(page.locator(f'[data-spanish-field="{field}"] .ai-spanish-english')).to_have_text(source[field])
                assert page.locator('#ai-spanish-preview').locator('[onerror], script').count() == 0
                leak_check(UNKNOWN_KEY)
                print(f'PASS AI card D {provider}: native shape, brand prompt, scoped fields and review-only preview')

            # Optional social fields are absent from both schema and prompt when
            # their source boxes are empty.
            set_post_fields('', '')
            expected_without_social = {key: source[key] for key in FLYER_FIELDS}
            translate(expected_without_social)
            wait_done()
            validate_request('claude', calls[-1], expected_without_social)
            for field in SOCIAL_FIELDS:
                assert source[field] not in json.dumps(calls[-1]['body'], ensure_ascii=False)
            set_post_fields(source['instagramCaption'], source['facebookDescription'])

            # Card D uses strict JSON. Fences or commentary do not replace a
            # valid earlier preview.
            preview_before = spanish_values()
            translate('```json\n' + json.dumps(translated) + '\n```')
            wait_done()
            expect(page.locator('#ai-spanish-status')).to_contain_text(re.compile('JSON', re.I))
            assert spanish_values() == preview_before
            assert brief() == english_form
            print('PASS AI card D: strict JSON rejects fenced output and preserves prior preview')

            # AI text is whitespace-trimmed but never clipped. Overlength text
            # stays editable with a direct hint and cannot be saved as a draft.
            long_headline = 'Esta oración sigue siendo importante. ' * 5
            too_long = {**translated, 'headline': '  ' + long_headline + '  '}
            translate(too_long)
            wait_done()
            expect(page.locator('#ai-spanish-headline')).to_have_value(long_headline.strip())
            assert len(page.locator('#ai-spanish-headline').input_value()) > 140
            expect(page.locator('[data-spanish-field="headline"]')).to_contain_text(re.compile('too long.*shorten', re.I))
            expect(page.locator('#ai-spanish-save')).to_be_disabled()
            page.locator('#ai-spanish-headline').fill(translated['headline'])
            expect(page.locator('#ai-spanish-save')).to_be_enabled()
            print('PASS AI card D: overlength Spanish remains editable, is never silently cut, and blocks save')

            # Missing and altered numbers, street addresses and URLs are flagged
            # beside the affected Spanish field. Exact protected content clears
            # the warning.
            for unsafe_body in ('Una reunión para todos.',
                                'Jordan Lee tiene 26 boletos en 124 Main Street. Visita https://changed.test/.'):
                translate({**translated, 'body': unsafe_body})
                wait_done()
                warning = page.locator('[data-spanish-warning="body"]')
                expect(warning).to_be_visible()
                expect(warning).to_contain_text(re.compile('number|address|link|url|missing|changed', re.I))
                assert brief() == english_form
            translate(translated)
            wait_done()
            expect(page.locator('[data-spanish-warning="body"]')).to_be_hidden()
            print('PASS AI card D: missing or altered numbers, address and URL are flagged next to the field')

            # Cancel, provider failure and the real 30-second timeout keep both
            # the English source and the last complete Spanish preview.
            preview_before = spanish_values()
            translate({}, mode='hold')
            expect(page.locator('#ai-spanish-button')).to_contain_text('Working')
            page.locator('#ai-spanish-cancel-button').click()
            wait_done()
            expect(page.locator('#ai-spanish-status')).to_contain_text(re.compile('cancel', re.I))
            assert brief() == english_form and spanish_values() == preview_before
            translate({}, mode=400)
            wait_done()
            expect(page.locator('#ai-spanish-status')).not_to_contain_text(FAKE_KEY)
            expect(page.locator('#ai-spanish-status')).not_to_contain_text(UNKNOWN_KEY)
            assert brief() == english_form and spanish_values() == preview_before
            translate({}, mode='hold')
            wait_done()
            expect(page.locator('#ai-spanish-status')).to_contain_text(re.compile('30 seconds|timed out', re.I))
            assert brief() == english_form and spanish_values() == preview_before
            leak_check(UNKNOWN_KEY)
            print('PASS AI card D: cancellation, sanitized provider failure and real timeout preserve both versions')

            # Hostile output is inserted as editable text only and key-looking
            # strings are redacted before they can reach DOM text or storage.
            hostile_markup = '<img src=x onerror="window.__spanishHostile=1">'
            hostile = {**translated, 'headline': hostile_markup + UNKNOWN_KEY,
                       'cta': hostile_markup + FAKE_KEY}
            translate(hostile)
            wait_done()
            expect(page.locator('#ai-spanish-headline')).to_have_value(hostile_markup + '[key removed]')
            expect(page.locator('#ai-spanish-cta')).to_have_value(hostile_markup + '[key removed]')
            assert page.locator('img[src="x"], [onerror]').count() == 0
            assert page.evaluate('window.__spanishHostile === undefined')
            leak_check(UNKNOWN_KEY)
            print('PASS AI card D: provider text is text-only and key echoes are redacted')

            # Unicode survives a failed save, a successful separate save, drawer
            # rendering, JSON export and draft recovery after reload.
            translate(unicode_result)
            wait_done()
            library_before_failure = page.evaluate('(k) => localStorage.getItem(k)', BRIEFS_KEY)
            page.evaluate('''k => {
              window.__spanishSetItem = Storage.prototype.setItem;
              Storage.prototype.setItem = function(name, value) {
                if (name === k) throw new DOMException('Quota exceeded', 'QuotaExceededError');
                return window.__spanishSetItem.call(this, name, value);
              };
            }''', BRIEFS_KEY)
            page.locator('#ai-spanish-save').click()
            expect(page.locator('#ai-spanish-save-status')).to_contain_text(re.compile('not saved|could not|couldn.t|storage|space|full', re.I))
            assert page.evaluate('(k) => localStorage.getItem(k)', BRIEFS_KEY) == library_before_failure
            assert brief() == english_form
            page.evaluate('''() => {
              Storage.prototype.setItem = window.__spanishSetItem;
              delete window.__spanishSetItem;
            }''')
            page.locator('#ai-spanish-save').click()
            expect(page.locator('#ai-spanish-save-status')).to_contain_text(re.compile('saved|my flyers', re.I))
            assert brief() == english_form, 'Separate Spanish save changed the English form'
            assert page.evaluate('(k) => localStorage.getItem(k)', DRAFT_KEY) == english_draft

            library = json.loads(page.evaluate('(k) => localStorage.getItem(k)', BRIEFS_KEY))
            assert len(library) == 2
            english_after = next(item for item in library if not item['payload'].get('translation'))
            spanish_entry = next(item for item in library if item['payload'].get('translation'))
            assert english_after['payload'] == english_library[0]['payload']
            payload = spanish_entry['payload']
            assert payload['translation'] == {
                'language': 'es', 'reviewNote': REVIEW_NOTE,
                'name': source['headline'] + ' (Spanish)',
                'social': {field: unicode_result[field] for field in SOCIAL_FIELDS},
            }
            for field, value in english_form['values'].items():
                if field not in FLYER_FIELDS:
                    assert payload['values'][field] == value, f'Non-translated field changed: {field}'
            assert payload['photo'] == english_form['photo']
            for field in FLYER_FIELDS:
                assert payload['values'][field] == unicode_result[field]
            saved_text = json.dumps(spanish_entry, ensure_ascii=False)
            for character in ('ñ', '¿', '¡', 'á'):
                assert character in saved_text
            assert FAKE_KEY not in saved_text and UNKNOWN_KEY not in saved_text

            page.locator('#open-briefs').click()
            spanish_card = page.locator('.brief-card', has_text=source['headline'] + ' (Spanish)')
            expect(spanish_card).to_be_visible()
            expect(spanish_card).to_contain_text(REVIEW_NOTE)
            spanish_card.locator('.brief-open').click()
            for field in FLYER_FIELDS:
                expect(page.locator('#' + field)).to_have_value(unicode_result[field])
            assert brief()['translation'] == payload['translation']
            expect(page.locator('#ai-instagram-caption')).to_have_value(unicode_result['instagramCaption'])
            expect(page.locator('#ai-facebook-description')).to_have_value(unicode_result['facebookDescription'])
            expect(page.locator('body')).to_contain_text(REVIEW_NOTE)
            page.wait_for_timeout(400)
            with page.expect_download() as download:
                page.locator('#export-brief').click()
            exported = output_dir / 'spanish-unicode-brief.json'
            download.value.save_as(str(exported))
            exported_text = exported.read_text(encoding='utf-8')
            exported_data = json.loads(exported_text)
            assert exported_data['payload']['translation'] == payload['translation']
            for character in ('ñ', '¿', '¡', 'á'):
                assert character in exported_text
            assert FAKE_KEY not in exported_text and UNKNOWN_KEY not in exported_text

            call_count = len(calls)
            page.reload()
            ready()
            for field in FLYER_FIELDS:
                expect(page.locator('#' + field)).to_have_value(unicode_result[field])
            assert brief()['translation'] == payload['translation']
            expect(page.locator('body')).to_contain_text(REVIEW_NOTE)
            assert len(calls) == call_count, 'Reloading a saved Spanish draft made an AI request'
            leak_check(UNKNOWN_KEY)
            print('PASS AI card D: separate draft, review note, exact fixed fields, storage failure, Unicode save/export/reload')

            page.set_viewport_size({'width': 390, 'height': 844})
            page.locator('#ai-spanish-button').scroll_into_view_if_needed()
            assert page.locator('#ai-spanish-button').bounding_box()['height'] >= 44
            if page.locator('#ai-spanish-preview').is_visible():
                assert page.locator('#ai-spanish-preview').evaluate('e => e.scrollWidth <= e.clientWidth + 1')
                page.locator('#ai-spanish-preview').screenshot(path=str(output_dir / 'ai-spanish-phone.png'))
            print('PASS AI card D: phone preview has no horizontal overflow and tap target is usable')
        finally:
            for route, _provider in held:
                try:
                    route.abort()
                except Exception:
                    pass
            context.close()

    print('PASS AI card D Spanish version: all mocked provider, preservation, draft and safety checks (none skipped)')


def check_spanish(chrome, output_dir):
    """Run Card D checks and report assertions through the main receipt path."""
    checks = sys.modules.get('__main__')
    if not hasattr(checks, 'CheckFailure'):
        import check_factory as checks
    try:
        _check_spanish(chrome, output_dir)
    except checks.CheckFailure:
        raise
    except Exception as error:
        detail = str(error) or 'an acceptance assertion failed'
        raise checks.CheckFailure(f'Spanish AI acceptance: {detail}') from error
