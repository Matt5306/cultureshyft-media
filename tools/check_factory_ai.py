"""Factory AI acceptance: intercepted providers only, no server or real keys.

Called unconditionally by the default check_factory.py run. Can also be run
directly for a focused repair. All HTTP(S) traffic is intercepted, including
unknown destinations. Browser evidence is retained in the existing scratch area.
"""
from __future__ import annotations

import json
import re
import sys
import uuid

AI_KEY = 'cultureshyft.factory.ai.v1'
FAKE_KEY = 'sk-' + 'TEST' + 'FAKE' * 8  # built at runtime so the secret scanner never sees a key-shaped literal
UNKNOWN_KEYS = tuple(prefix + 'UNKNOWN' + 'TEST' * 8
                     for prefix in ('AIza', 'sk-', 'sk-proj-', 'sk-ant-', 'sk-or-'))
FIELDS = ('headline', 'subheadline', 'body', 'cta')
SUGGESTION = dict(zip(FIELDS, ('Meet your neighbors.', 'Make room for connection.',
                             'Local makers. Good food. Everyone is welcome.', 'Come through.')))
VERSIONS = [dict(label=label, **{field: f'{label} {value}' for field, value in SUGGESTION.items()})
            for label in ('Bold', 'Warm', 'Short')]
POST_RESULT = {
    'instagram_caption': 'Meet your neighbors. Local makers, good food and room for everyone.',
    'hashtags': ['#CultureShyft', 'Detroit!', '#detroit', 'Community Event', '#Neighbors'],
    'facebook_description': 'Meet your neighbors at the Community Room. Local makers and good food bring everyone together.',
}
KEY_URLS = {
    'gemini': 'https://aistudio.google.com/apikey',
    'openai': 'https://platform.openai.com/api-keys',
    'claude': 'https://console.anthropic.com/settings/keys',
    'openrouter': 'https://openrouter.ai/settings/keys',
}
PROVIDERS = {
    'gemini': ('Gemini', 'gemini-3.6-flash', 'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent'),
    'openai': ('OpenAI', 'gpt-6-luna', 'https://api.openai.com/v1/chat/completions'),
    'claude': ('Claude', 'claude-haiku-5-5', 'https://api.anthropic.com/v1/messages'),
    'openrouter': ('OpenRouter', 'example/test-model', 'https://openrouter.ai/api/v1/chat/completions'),
    'local': ('Local AI', 'test-local-model', 'http://localhost:1234/v1/chat/completions'),
}


def check_ai(chrome, output_dir):
    checks = sys.modules.get('__main__')
    if not hasattr(checks, 'FACTORY_PAGE'):
        import check_factory as checks
    from playwright.sync_api import sync_playwright, expect

    output_dir.mkdir(parents=True, exist_ok=True)
    profile = checks.SCRATCH_DIR / f'ai-{uuid.uuid4().hex}'
    profile.mkdir(parents=True)
    calls, console, errors, held = [], [], [], []
    mock = {'provider': 'gemini', 'mode': 'success', 'text': None}

    def resize(page, width, height):
        # The flyer preview rescales from resize/ResizeObserver callbacks after
        # the viewport changes, which shifts everything below it. Wait two
        # frames so layout assertions measure the settled page, not a race.
        page.set_viewport_size({'width': width, 'height': height})
        page.evaluate('() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))')

    def response(text):
        if mock['provider'] == 'gemini':
            return {'candidates': [{'content': {'parts': [{'text': text}]}, 'finishReason': 'STOP'}]}
        if mock['provider'] == 'claude':
            return {'content': [{'type': 'text', 'text': text}], 'stop_reason': 'end_turn'}
        return {'choices': [{'message': {'content': text}, 'finish_reason': 'stop'}]}

    def route_request(route):
        request = route.request
        if not request.url.startswith(('http:', 'https:')):
            route.continue_()
            return
        calls.append({'url': request.url, 'headers': request.headers,
                      'method': request.method, 'body': request.post_data_json})
        mode = mock['mode']
        if mode == 'offline':
            route.abort('internetdisconnected')
        elif mode == 'hold':
            held.append(route)
        elif isinstance(mode, int):
            route.fulfill(status=mode, content_type='application/json', body=json.dumps({
                'error': {'message': 'API key not valid ' + FAKE_KEY + ' ' + UNKNOWN_KEYS[0], 'code': mode}}))
        elif mode == 'blocked':
            route.fulfill(json={'promptFeedback': {'blockReason': 'SAFETY'}, 'candidates': []})
        elif mode == 'empty':
            route.fulfill(json={'candidates': []})
        elif mode == 'partial_blocked':
            route.fulfill(json={'candidates': [{'content': {'parts': [{'text': json.dumps(SUGGESTION)}]}, 'finishReason': 'SAFETY'}]})
        elif mode == 'invalid_response':
            route.fulfill(content_type='application/json', body='not JSON')
        else:
            text = mock['text'] if mock['text'] is not None else json.dumps(SUGGESTION)
            route.fulfill(json=response(text))

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

        def values():
            return page.evaluate('() => factoryBrief.collect().values')

        def leak_check():
            assert FAKE_KEY not in page.content(), 'Key leaked into DOM markup'
            assert FAKE_KEY not in page.locator('body').text_content(), 'Key leaked into DOM text'
            assert FAKE_KEY not in json.dumps(page.evaluate('factoryBrief.collect()')), 'Key in brief'
            storage = page.evaluate('''() => Object.fromEntries(Object.keys(localStorage)
              .filter(k => k !== 'cultureshyft.factory.ai.v1').map(k => [k, localStorage.getItem(k)]))''')
            assert FAKE_KEY not in json.dumps(storage), 'Key leaked outside AI settings'
            assert all(FAKE_KEY not in call['url'] for call in calls), 'Key leaked into URL'
            assert FAKE_KEY not in '\n'.join(console + errors), 'Key leaked into diagnostics'
            assert not errors, errors

        def open_settings():
            if not page.locator('#ai-settings-dialog').is_visible():
                page.locator('#open-ai-settings').click()

        def choose(provider):
            mock.update(provider=provider, mode='success', text=None)
            open_settings()
            page.locator('#ai-provider').select_option(provider)
            model = PROVIDERS[provider][1]
            if provider in ('openrouter', 'local'):
                page.locator('#ai-model').fill(model)
            else:
                expect(page.locator('#ai-model')).to_have_value(model)
            if provider == 'local':
                expect(page.locator('#ai-base-url')).to_have_value('http://localhost:1234/v1')
            else:
                page.locator('#ai-api-key').fill(FAKE_KEY)
            return model

        def save_settings():
            page.locator('#ai-save-settings').click()
            expect(page.locator('#ai-settings-dialog')).not_to_be_visible()

        def write(mode='success', text=None):
            mock.update(mode=mode, text=text)
            page.locator('#ai-write-button').click()

        def wait_done():
            expect(page.locator('#ai-write-button')).to_have_text('Write it for me', timeout=40000)

        def post(mode='success', text=None):
            mock.update(mode=mode, text=text)
            page.locator('#ai-post-button').click()

        def wait_post_done():
            expect(page.locator('#ai-post-button')).to_have_text('Write the post', timeout=40000)

        def post_values():
            return {name: page.locator(selector).input_value() for name, selector in {
                'instagram_caption': '#ai-instagram-caption',
                'hashtags': '#ai-hashtags',
                'facebook_description': '#ai-facebook-description',
            }.items()}

        def validate_request(provider, call, is_test=False):
            assert call['method'] == 'POST'
            assert call['url'] == PROVIDERS[provider][2], call['url']
            assert FAKE_KEY not in call['url']
            headers, body = call['headers'], call['body']
            if provider == 'gemini':
                assert headers['x-goog-api-key'] == FAKE_KEY
                assert 'authorization' not in headers
                assert body['generationConfig']['responseMimeType'] == 'application/json'
                assert body.get('systemInstruction') and body.get('contents')
                user_text = body['contents'][0]['parts'][0]['text']
            elif provider == 'claude':
                assert headers['x-api-key'] == FAKE_KEY
                assert headers['anthropic-version'] == '2023-06-01'
                assert headers['anthropic-dangerous-direct-browser-access'] == 'true'
                assert body['model'] == PROVIDERS[provider][1] and body.get('max_tokens')
                assert body.get('system') and body['messages'][0]['role'] == 'user'
                user_text = body['messages'][0]['content']
            else:
                if provider != 'local':
                    assert headers['authorization'] == 'Bearer ' + FAKE_KEY
                else:
                    assert FAKE_KEY not in json.dumps(headers), 'Cloud key sent to Local AI'
                assert body['model'] == PROVIDERS[provider][1]
                assert [m['role'] for m in body['messages']] == ['system', 'user']
                user_text = body['messages'][1]['content']
            serialized = json.dumps(body)
            for private in ('PRIVATE_CONTACT', 'PRIVATE_CLIENT', 'private-reply@example.com', 'private-qr.example', 'data:image/'):
                assert private not in serialized, 'Private field sent to provider'
            assert FAKE_KEY not in serialized
            if is_test:
                assert len(user_text) < 250, 'Test prompt should be tiny'
                assert 'Original headline' not in user_text
            else:
                for field in ('headline', 'subheadline', 'date', 'place', 'body', 'cta'):
                    assert page.locator('#' + field).input_value() in user_text, f'{field} missing from AI prompt'
                assert 'community' in user_text.lower(), 'Selected occasion missing'
                system = (body['systemInstruction']['parts'][0]['text'] if provider == 'gemini'
                          else body['system'] if provider == 'claude' else body['messages'][0]['content'])
                voice = page.evaluate('factoryAI.BRAND_VOICE')
                assert voice and voice in system, 'Generation does not reuse the exported brand voice'
                for term in ('versions', 'Bold', 'Warm', 'Short', 'JSON'):
                    assert term in system, f'Missing structured instruction: {term}'
                if provider == 'gemini':
                    schema = body['generationConfig']['responseSchema']
                    versions = schema['properties']['versions']
                    assert versions['minItems'] == versions['maxItems'] == 3
                    assert set(versions['items']['required']) == {'label', *FIELDS}
                    assert body['generationConfig']['maxOutputTokens'] >= 2000
                elif provider != 'claude':
                    assert body['response_format']['type'] == 'json_object'

        def validate_post_request(provider, call):
            assert call['method'] == 'POST'
            assert call['url'] == PROVIDERS[provider][2], call['url']
            assert FAKE_KEY not in call['url']
            headers, body = call['headers'], call['body']
            if provider == 'gemini':
                assert headers['x-goog-api-key'] == FAKE_KEY
                user_text = body['contents'][0]['parts'][0]['text']
                system = body['systemInstruction']['parts'][0]['text']
                schema = body['generationConfig']['responseSchema']
                assert set(schema['required']) == {'instagram_caption', 'hashtags', 'facebook_description'}
                assert schema['properties']['hashtags']['maxItems'] == 8
            elif provider == 'claude':
                assert headers['x-api-key'] == FAKE_KEY
                assert headers['anthropic-dangerous-direct-browser-access'] == 'true'
                user_text = body['messages'][0]['content']
                system = body['system']
            else:
                assert headers['authorization'] == 'Bearer ' + FAKE_KEY
                user_text = body['messages'][1]['content']
                system = body['messages'][0]['content']
                assert body['response_format']['type'] == 'json_object'
            sent = json.loads(user_text.split('Flyer fields: ', 1)[1])
            assert set(sent) == {'headline', 'subheadline', 'date', 'place', 'body', 'cta'}
            assert sent == {field: page.locator('#' + field).input_value()
                            for field in ('headline', 'subheadline', 'date', 'place', 'body', 'cta')}
            serialized = json.dumps(body)
            for private in ('PRIVATE_CONTACT', 'PRIVATE_CLIENT', 'private-reply@example.com',
                            'private-qr.example', 'data:image/', 'Community event'):
                assert private not in serialized, f'Private or out-of-scope post field sent: {private}'
            assert FAKE_KEY not in serialized
            voice = page.evaluate('factoryAI.BRAND_VOICE')
            assert voice in system
            for rule in ('instagram_caption', 'hashtags', 'facebook_description', '2200', '125',
                         'Return no more than 8 relevant hashtags', '1000', '5000', 'no emoji', 'date, time and address exactly'):
                assert rule.lower() in system.lower(), f'Missing post rule: {rule}'

        try:
            page.goto(checks.FACTORY_PAGE.as_uri()); ready()
            assert not calls, 'AI requested on page load'
            # Compare actual exported prompt content with the authoritative brand
            # sections, so edits to either source cannot silently drift apart.
            voice_doc = (checks.ROOT / 'brand/brand-voice.md').read_text(encoding='utf-8')
            voice = page.evaluate('factoryAI.BRAND_VOICE')
            for section in ('Tagline (fixed)', 'Tone words', 'How we write'):
                content = voice_doc.split('## ' + section + '\n', 1)[1].split('\n## ', 1)[0]
                for line in content.strip().splitlines():
                    rule = line.removeprefix('- ').replace('**', '').strip()
                    if rule:
                        assert rule in voice, f'Brand voice drift: {rule}'
            for term in ('Media made to move people.', 'collateral', 'clients', 'Culture Shift',
                         'game-changing', 'revolutionary', 'unleash', 'no emoji in headlines'):
                assert term in voice, f'Brand voice missing required rule: {term}'
            print('PASS AI card A: exported brand voice matches brand document, exact tagline and avoid-list')
            expect(page.locator('#ai-post-button')).to_be_disabled()
            page.locator('#ai-write-button').click()
            expect(page.locator('#ai-settings-dialog')).to_be_visible()
            expect(page.locator('#ai-provider')).to_have_value('gemini')
            expect(page.locator('#ai-api-key')).to_have_attribute('type', 'password')
            page.keyboard.press('Escape')
            expect(page.locator('#ai-settings-dialog')).not_to_be_visible()
            expect(page.locator('#ai-write-button')).to_be_focused()
            page.locator('#preset').select_option('community-event')
            expect(page.locator('#ai-post-button')).to_be_enabled()
            page.locator('#contact').fill('')
            expect(page.locator('#ai-post-button')).to_be_disabled()
            page.locator('#contact').fill('PRIVATE_CONTACT')
            expect(page.locator('#ai-post-button')).to_be_enabled()
            page.locator('#ai-post-button').click()
            expect(page.locator('#ai-settings-dialog')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('#ai-post-button')).to_be_focused()
            print('PASS AI card B: required-field readiness follows preset/programmatic input and unconfigured tap opens helper')
            original = {'headline': 'Original headline', 'subheadline': 'Original subhead',
                        'date': 'October 24 at 2 PM', 'place': 'Community room',
                        'body': 'Original body\nSecond line.', 'cta': 'Original action'}
            for field, value in original.items():
                page.locator('#' + field).fill(value)
            page.locator('#contact').fill('PRIVATE_CONTACT')
            page.locator('.order-details').evaluate('e => e.open = true')
            page.locator('#clientName').fill('PRIVATE_CLIENT')
            page.locator('#clientEmail').fill('private-reply@example.com')
            page.locator('#qr-url').fill('https://private-qr.example/')
            page.evaluate('''() => {
              const canvas = document.createElement('canvas'); canvas.width = canvas.height = 2;
              window.factoryPhoto.setState({dataUrl: canvas.toDataURL('image/png'), zoom: 1, focusX: .5, focusY: .5});
            }''')
            page.locator('#save-brief').click()
            before = values()
            original_photo = page.evaluate('factoryBrief.collect().photo')
            assert not calls, 'AI requested while typing or saving'

            # Three choices use one request in each adapter; all apply buttons
            # operate on their own version and preserve the exact prior brief.
            for provider in PROVIDERS:
                count = len(calls)
                choose(provider)
                if provider == 'local':
                    expect(page.locator('#ai-key-link')).not_to_be_visible()
                    expect(page.locator('#ai-local-note')).to_contain_text('no key')
                else:
                    link = page.locator('#ai-key-link')
                    expect(link).to_be_visible()
                    expect(link).to_have_attribute('href', KEY_URLS[provider])
                    expect(link).to_have_attribute('target', '_blank')
                    assert {'noopener', 'noreferrer'} <= set(link.get_attribute('rel').split())
                    assert page.evaluate('(p) => factoryAI.PROVIDERS[p].keyUrl', provider) == KEY_URLS[provider]
                    if provider == 'gemini':
                        expect(link).to_have_text('Get a free Gemini key')
                save_settings()
                assert len(calls) == count, 'Provider/key link setup caused network activity'
                write(text=json.dumps({'versions': VERSIONS})); wait_done()
                assert len(calls) == count + 1, 'Three versions must use exactly one request'
                validate_request(provider, calls[-1])
                assert values() == before
                cards = page.locator('[data-ai-version]')
                assert cards.count() == 3
                for index, version in enumerate(VERSIONS):
                    card = cards.nth(index)
                    expect(card.locator('.ai-version-title')).to_have_text(version['label'])
                    for field in FIELDS:
                        expect(card.locator(f'[data-ai-field="{field}"] .ai-suggested')).to_have_text(version[field])
                        card.locator(f'[data-ai-use="{field}"]').click()
                        assert values() == {**before, field: version[field]}
                        page.locator('#ai-undo').click()
                        assert values() == before
                    card.locator('[data-ai-use-all]').click()
                    assert values() == {**before, **{field: version[field] for field in FIELDS}}
                    page.locator('#ai-undo').click()
                    assert values() == before
                cards.nth(1).locator('[data-ai-use-all]').click()
                write(text=json.dumps({'versions': VERSIONS})); wait_done()
                expect(page.locator('#ai-undo')).to_be_visible()
                page.locator('#ai-undo').click()
                assert values() == before, 'New multi-version reply cleared the exact Undo snapshot'
                if provider in ('gemini', 'openai', 'claude'):
                    post_count = len(calls)
                    post(text='```json\n' + json.dumps(POST_RESULT) + '\n```'); wait_post_done()
                    assert len(calls) == post_count + 1, 'Post generation must use exactly one request'
                    validate_post_request(provider, calls[-1])
                    assert post_values() == {
                        'instagram_caption': POST_RESULT['instagram_caption'],
                        'hashtags': '#CultureShyft #Detroit #CommunityEvent #Neighbors',
                        'facebook_description': POST_RESULT['facebook_description'],
                    }
                    assert values() == before, 'Post generation changed the flyer brief'
                    expect(page.locator('#ai-post-results')).to_be_visible()
                    # Reject empty and partially empty replies atomically, even
                    # after Mark has edited all three boxes. Exercise each adapter.
                    page.locator('#ai-instagram-caption').fill('My edited caption')
                    page.locator('#ai-hashtags').fill('#MyEditedTag')
                    page.locator('#ai-facebook-description').fill('My edited description')
                    edited_post = post_values()
                    for caption, description in (('', ''), (' \t\n', ' \n\t'),
                                                  ('', 'Usable description'), ('Usable caption', ''),
                                                  (' \t', 'Usable description'), ('Usable caption', '\n ')):
                        count_before = len(calls)
                        post(text=json.dumps({'instagram_caption': caption, 'hashtags': [],
                                              'facebook_description': description}))
                        wait_post_done()
                        expect(page.locator('#ai-post-status')).to_contain_text('empty caption or description')
                        expect(page.locator('#ai-post-status')).to_contain_text('earlier post is unchanged')
                        expect(page.locator('#ai-post-results')).to_be_visible()
                        assert post_values() == edited_post
                        assert len(calls) == count_before + 1
                        assert values() == before
                    post(text=json.dumps(dict(POST_RESULT, hashtags=[]))); wait_post_done()
                    expect(page.locator('#ai-post-status')).to_contain_text('Your post is ready')
                    expect(page.locator('#ai-hashtags')).to_have_value('')
                leak_check()
                print(f'PASS AI card A {provider}: key guidance, one request, 3 labelled choices, per-version/field apply and Undo')
                if provider in ('gemini', 'openai', 'claude'):
                    print(f'PASS AI card B {provider}: native shape, schema, privacy, blank/partial reply rejection, edited-copy preservation and recovery')

            for width, height in ((1440, 1200), (390, 844)):
                resize(page, width, height)
                # Measure all cards in one layout snapshot so a late reflow
                # cannot land between them.
                boxes = page.locator('[data-ai-version]').evaluate_all(
                    'cards => cards.map(c => { const r = c.getBoundingClientRect(); return {x: r.x, y: r.y}; })')
                assert len(boxes) == 3, f'Expected 3 version cards, got {len(boxes)}'
                if width == 1440:
                    assert max(b['y'] for b in boxes) - min(b['y'] for b in boxes) < 2, f'Versions not side by side: {boxes}'
                    assert boxes[0]['x'] < boxes[1]['x'] < boxes[2]['x']
                else:
                    assert boxes[0]['y'] < boxes[1]['y'] < boxes[2]['y'], 'Versions not stacked on phone'
                assert page.locator('#ai-suggestions').evaluate('e => e.scrollWidth <= e.clientWidth + 1')
                for button in page.locator('[data-ai-version] button').all():
                    assert button.bounding_box()['height'] >= 44
                page.locator('#ai-suggestions').screenshot(path=str(output_dir / f'ai-versions-{width}.png'))
            page.set_viewport_size({'width': 1024, 'height': 1366})
            print('PASS AI card A: side-by-side desktop and stacked phone choices, no overflow, touch targets')

            # Post parser limits and hashtag cleanup are enforced after parsing,
            # including a sentence mark exactly one character beyond each cap.
            choose('gemini'); save_settings()
            limits = page.evaluate('factoryAI.POST_LIMITS')
            assert limits == {'instagramCaption': 2200, 'instagramHook': 125, 'hashtags': 8,
                              'facebookAim': 1000, 'facebookDescription': 5000}
            assert page.locator('#ai-instagram-caption').get_attribute('maxlength') == str(limits['instagramCaption'])
            assert page.locator('#ai-facebook-description').get_attribute('maxlength') == str(limits['facebookDescription'])
            capped = {
                'instagram_caption': 'A' * limits['instagramCaption'] + '. trailing words',
                'hashtags': [' Culture Shyft ', '#Detroit!', '#detroit', 'one', 'two', 'three',
                             'four', 'five', 'six', 'seven', 'eight', 'nine'],
                'facebook_description': 'B' * limits['facebookDescription'] + '. trailing words',
            }
            post(text='Provider preface\n```json\n' + json.dumps(capped) + '\n```\nend'); wait_post_done()
            capped_values = post_values()
            assert len(capped_values['instagram_caption']) == limits['instagramCaption']
            assert len(capped_values['facebook_description']) == limits['facebookDescription']
            tags = capped_values['hashtags'].split()
            assert tags == ['#CultureShyft', '#Detroit', '#one', '#two', '#three', '#four', '#five', '#six']
            assert all(re.fullmatch(r'#[A-Za-z0-9]+', tag) for tag in tags)
            expect(page.locator('#ai-instagram-count')).to_have_text('2,200 / 2,200 characters')
            expect(page.locator('#ai-facebook-count')).to_have_text('5,000 / 5,000 characters · Aim for 1,000 or fewer')
            expect(page.locator('#ai-instagram-hook')).to_have_text('Hook preview (first 125 characters): ' + 'A' * 125)
            expect(page.locator('#ai-hashtags-count')).to_contain_text('8 / 8 hashtags')
            bounded = page.evaluate('''limits => factoryAI.parsePost(JSON.stringify({
              instagram_caption: 'word '.repeat(420) + 'Stop. ' + 'tail '.repeat(100),
              hashtags: [], facebook_description: 'word '.repeat(1100)
            }))''', limits)
            assert bounded['instagramCaption'].endswith('Stop.')
            assert len(bounded['instagramCaption']) <= limits['instagramCaption']
            assert bounded['facebookDescription'].endswith('word')
            assert len(bounded['facebookDescription']) <= limits['facebookDescription']
            exact_word = 'a' * (limits['instagramCaption'] - 5) + ' word'
            exact_post = page.evaluate('''text => factoryAI.parsePost(JSON.stringify({
              instagram_caption: text + ' more', hashtags: [], facebook_description: 'Valid description'
            }))''', exact_word)
            assert exact_post['instagramCaption'] == exact_word, 'Dropped a complete word exactly at the cap'
            print('PASS AI card B: fenced parser, sentence/word boundaries, hard caps including off-by-one, 8 cleaned de-duplicated hashtags')

            # The boxes are editable for this page, counts stay live, and both
            # clipboard paths copy only normalized plain text.
            page.locator('#ai-instagram-caption').fill('Five')
            expect(page.locator('#ai-instagram-count')).to_have_text('4 / 2,200 characters')
            expect(page.locator('#ai-instagram-hook')).to_have_text('Hook preview (first 125 characters): Five')
            page.evaluate('''() => Object.defineProperty(navigator, 'clipboard', {configurable: true,
              value: {writeText: async text => { window.__copiedText = text; }}})''')
            page.locator('[data-ai-copy="ai-instagram-caption"]').click()
            expect(page.locator('#ai-instagram-copy-status')).to_have_text('Copied')
            assert page.evaluate('window.__copiedText') == 'Five'
            page.locator('#ai-hashtags').fill('Culture-Shyft #Detroit #detroit #One #Two #Three #Four #Five #Six #Seven #Eight #Nine')
            page.locator('[data-ai-copy="ai-hashtags"]').click()
            expect(page.locator('#ai-hashtags-copy-status')).to_have_text('Copied')
            copied_tags = page.evaluate('window.__copiedText')
            assert copied_tags == '#CultureShyft #Detroit #One #Two #Three #Four #Five #Six'
            expect(page.locator('#ai-hashtags-count')).to_contain_text('8 / 8 hashtags')
            page.locator('#ai-facebook-description').fill('Fallback copy')
            page.evaluate('''() => {
              navigator.clipboard.writeText = async () => { throw new Error('blocked'); };
              document.execCommand = command => {
                const field = document.activeElement;
                window.__fallbackText = command === 'copy' ? field.value.slice(field.selectionStart, field.selectionEnd) : '';
                return command === 'copy';
              };
            }''')
            page.locator('[data-ai-copy="ai-facebook-description"]').click()
            expect(page.locator('#ai-facebook-copy-status')).to_have_text('Copied')
            assert page.evaluate('window.__fallbackText') == 'Fallback copy'
            for failure in ('false', 'throw'):
                page.evaluate('''failure => {
                  document.execCommand = () => {
                    if (failure === 'throw') throw new Error('Copy blocked');
                    return false;
                  };
                }''', failure)
                page.locator('[data-ai-copy="ai-facebook-description"]').click()
                expect(page.locator('#ai-facebook-copy-status')).to_have_text('Text selected. Use Copy in your browser.')
                expect(page.locator('#ai-facebook-description')).to_be_focused()
                assert page.locator('#ai-facebook-description').evaluate('e => e.value.slice(e.selectionStart, e.selectionEnd)') == 'Fallback copy'
            print('PASS AI card B: live counts/hook, clipboard success and blocked fallback recovery with selected text')

            # Hostile output remains text. Failed regeneration, provider errors,
            # cancellation and the real 30-second timeout preserve prior results.
            markup = '<script>window.__postHostile=1</script><img src=x onerror="window.__postHostile=1">'
            script_count = page.locator('script').count()
            echoed = {'instagram_caption': 'Echo ' + FAKE_KEY + ' ' + UNKNOWN_KEYS[0],
                      'hashtags': [FAKE_KEY, '#Prefix' + UNKNOWN_KEYS[0], '#Safe'],
                      'facebook_description': 'Echo ' + FAKE_KEY + ' ' + UNKNOWN_KEYS[0]}
            post(text=json.dumps(echoed)); wait_post_done()
            expect(page.locator('#ai-instagram-caption')).to_have_value('Echo [key removed] [key removed]')
            expect(page.locator('#ai-hashtags')).to_have_value('#Safe')
            expect(page.locator('#ai-facebook-description')).to_have_value('Echo [key removed] [key removed]')
            assert FAKE_KEY not in page.content() and UNKNOWN_KEYS[0] not in page.content()
            assert FAKE_KEY not in json.dumps(post_values()) and UNKNOWN_KEYS[0] not in json.dumps(post_values())
            safe_post = {'instagram_caption': markup, 'hashtags': ['#Safe'], 'facebook_description': 'SESSION_ONLY_MARKER'}
            post(text=json.dumps(safe_post)); wait_post_done()
            expect(page.locator('#ai-instagram-caption')).to_have_value(markup)
            assert page.locator('script').count() == script_count
            assert page.locator('img[src="x"], [onerror]').count() == 0
            assert page.evaluate('window.__postHostile === undefined')
            preserved = post_values()
            for mode, text_value, pattern in (('success', 'not JSON', r'JSON'), (429, None, r'wait|quota')):
                post(mode, text_value); wait_post_done()
                expect(page.locator('#ai-post-status')).to_contain_text(re.compile(pattern, re.I))
                assert post_values() == preserved
            post('hold')
            expect(page.locator('#ai-post-button')).to_have_text('Working...')
            page.locator('#ai-post-cancel-button').click(); wait_post_done()
            expect(page.locator('#ai-post-status')).to_contain_text(re.compile('cancel', re.I))
            assert post_values() == preserved
            post('hold'); wait_post_done()
            expect(page.locator('#ai-post-status')).to_contain_text(re.compile('30 seconds|timed out', re.I))
            assert post_values() == preserved
            print('PASS AI card B: key-echo redaction, hostile text safety and old-result preservation across malformed/error/cancel/real timeout')

            # Post copy never enters brief collection, autosave, saved flyers or
            # export, and a second page in the same browser starts with no post.
            assert 'SESSION_ONLY_MARKER' not in json.dumps(values())
            page.locator('#save-brief').click()
            saved_headline = page.locator('#headline').input_value()
            page.locator('#headline').fill('Autosave isolation check')
            page.wait_for_function('''() => JSON.parse(localStorage.getItem('cultureshyft.factory.draft.v1'))
              .payload.values.headline === 'Autosave isolation check' ''')
            assert page.evaluate('''() => JSON.parse(localStorage.getItem('cultureshyft.factory.briefs.v1'))
              .some(entry => entry.payload.values.headline === 'Autosave isolation check')''')
            non_ai_storage = page.evaluate('''() => Object.fromEntries(Object.keys(localStorage)
              .filter(k => k !== 'cultureshyft.factory.ai.v1').map(k => [k, localStorage.getItem(k)]))''')
            assert 'SESSION_ONLY_MARKER' not in json.dumps(non_ai_storage)
            with page.expect_download() as post_export:
                page.locator('#export-brief').click()
            post_export_path = output_dir / 'post-isolation-brief.json'
            post_export.value.save_as(str(post_export_path))
            assert 'SESSION_ONLY_MARKER' not in post_export_path.read_text(encoding='utf-8')
            page.locator('#headline').fill(saved_headline)
            fresh = context.new_page()
            fresh.goto(checks.FACTORY_PAGE.as_uri())
            fresh.evaluate('() => window.factoryReady')
            expect(fresh.locator('#ai-post-results')).to_be_hidden()
            for selector in ('#ai-instagram-caption', '#ai-hashtags', '#ai-facebook-description'):
                expect(fresh.locator(selector)).to_have_value('')
            fresh.close()
            for width, height in ((1440, 1200), (1024, 1366), (390, 844)):
                resize(page, width, height)
                assert page.locator('.ai-post').evaluate('e => e.scrollWidth <= e.clientWidth + 1')
                for button in page.locator('.ai-post button').all():
                    if button.is_visible(): assert button.bounding_box()['height'] >= 44
                page.locator('.ai-post').screenshot(path=str(output_dir / f'ai-post-{width}.png'))
            page.set_viewport_size({'width': 1024, 'height': 1366})
            print('PASS AI card B: session-only persistence/export isolation, reload reset, desktop/phone layout evidence')

            # Partial, sparse, fenced and prose-wrapped replies preserve usable
            # choices. Bad labels and key echoes must never become executable DOM.
            choose('gemini'); save_settings()
            for partial in ([VERSIONS[1]], [VERSIONS[0], VERSIONS[2]], [None, VERSIONS[1]]):
                write(text='Here are your options:\n```json\n' + json.dumps({'versions': partial}) + '\n```\nDone.'); wait_done()
                usable = [v for v in partial if v]
                cards = page.locator('[data-ai-version]')
                assert cards.count() == len(usable)
                expect(page.locator('#ai-write-status')).to_contain_text(str(len(usable)))
                assert values() == before
                for index, version in enumerate(usable):
                    expect(cards.nth(index).locator('.ai-version-title')).to_have_text(version['label'])
            hostile_versions = [dict(label='<img src=x onerror="window.__aiHostile=1">' + FAKE_KEY,
                                     **{field: '  ' + UNKNOWN_KEYS[0] + ' ' + 'A' * 600 + '  ' for field in FIELDS})
                                for _ in range(3)]
            write(text=json.dumps({'versions': hostile_versions})); wait_done()
            for card in page.locator('[data-ai-version]').all():
                for field, limit in zip(FIELDS, (140, 180, 450, 100)):
                    text = card.locator(f'[data-ai-field="{field}"] .ai-suggested').text_content()
                    assert len(text) == limit and text == text.strip()
                    assert text.startswith('[key removed]')
            assert UNKNOWN_KEYS[0] not in page.content()
            assert page.locator('img[src="x"], [onerror]').count() == 0
            assert page.evaluate('window.__aiHostile === undefined')
            leak_check()
            for invalid in ({'versions': []}, {'versions': [None, {'body': 'incomplete'}]}):
                write(text=json.dumps(invalid)); wait_done()
                expect(page.locator('#ai-write-status')).to_contain_text('JSON')
                assert values() == before
            print('PASS AI card A: partial/sparse replies, fences/prose, all version limits, label injection and key redaction')

            for provider in PROVIDERS:
                choose(provider)
                count = len(calls)
                if provider != 'local':
                    page.locator('#ai-show-key').click()
                    expect(page.locator('#ai-api-key')).to_have_attribute('type', 'text')
                    leak_check()
                    page.locator('#ai-show-key').click()
                assert len(calls) == count, 'Changing settings sent a request'
                page.locator('#ai-test-connection').click()
                expect(page.locator('#ai-settings-status')).to_contain_text('Connected.')
                validate_request(provider, calls[-1], is_test=True)
                assert len(calls) == count + 1
                save_settings()
                write(); wait_done()
                validate_request(provider, calls[-1])
                assert values() == before, 'Suggestion altered form before acceptance'
                expect(page.locator('#ai-suggestions')).to_be_visible()
                for field in FIELDS:
                    expect(page.locator(f'[data-ai-field="{field}"] .ai-current')).to_have_text(before[field])
                    expect(page.locator(f'[data-ai-field="{field}"] .ai-suggested')).to_have_text(SUGGESTION[field])
                leak_check()
                print(f'PASS AI {provider}: request shape, explicit test/write, privacy, review before apply')

            # Apply one field and undo; then apply all and undo, preserving every other control.
            page.locator('[data-ai-use="headline"]').click()
            assert values() == {**before, 'headline': SUGGESTION['headline']}
            page.locator('#ai-undo').click()
            assert values() == before
            page.locator('[data-ai-use-all]').click()
            assert values() == {**before, **SUGGESTION}
            page.wait_for_function('''() => JSON.parse(localStorage.getItem('cultureshyft.factory.draft.v1'))
              .payload.values.headline === 'Meet your neighbors.' ''')
            page.locator('#ai-undo').click()
            assert values() == before
            assert page.evaluate('factoryBrief.collect().photo') == original_photo
            page.wait_for_function('''() => JSON.parse(localStorage.getItem('cultureshyft.factory.draft.v1'))
              .payload.values.headline === 'Original headline' ''')
            page.locator('#headline').fill('Edited after request')
            page.locator('[data-ai-use="headline"]').click()
            page.locator('#ai-undo').click()
            expect(page.locator('#headline')).to_have_value('Edited after request')
            page.locator('#headline').fill(before['headline'])
            with page.expect_download() as download:
                page.locator('#export-brief').click()
            exported = output_dir / 'ai-brief.json'
            download.value.save_as(str(exported))
            assert FAKE_KEY not in exported.read_text(encoding='utf-8')
            leak_check()
            print('PASS AI: per-field/all acceptance, exact Undo, autosave, exported/saved/draft key isolation')

            # A arrives first; accept A while B is pending. B must preserve Undo.
            suggestion_b = {field: 'Second suggestion ' + field for field in FIELDS}
            write('hold')
            expect(page.locator('#ai-write-button')).to_contain_text('Working')
            page.locator('[data-ai-use="headline"]').click()
            assert values() == {**before, 'headline': SUGGESTION['headline']}
            held.pop().fulfill(json=response(json.dumps(suggestion_b)))
            wait_done()
            expect(page.locator('#ai-undo')).to_be_visible()
            page.locator('#ai-undo').click()
            assert values() == before
            # A later reply also preserves an already-established Undo snapshot.
            page.locator('[data-ai-use-all]').click()
            write(); wait_done()
            expect(page.locator('#ai-undo')).to_be_visible()
            page.locator('#ai-undo').click()
            assert values() == before
            # Another acceptance replaces the snapshot; editing copy invalidates it.
            page.locator('[data-ai-use="headline"]').click()
            page.locator('[data-ai-use="body"]').click()
            page.locator('#ai-undo').click()
            assert values() == {**before, 'headline': SUGGESTION['headline']}
            page.locator('#headline').fill(before['headline'])
            for field in FIELDS:
                page.locator('[data-ai-use-all]').click()
                page.locator('#' + field).fill('Manual edit')
                expect(page.locator('#ai-undo')).to_be_hidden()
                edited = values()
                page.locator('#ai-undo').dispatch_event('click')
                assert values() == edited, 'Stale Undo overwrote a manual edit'
                for name in FIELDS:
                    page.locator('#' + name).fill(before[name])
            print('PASS AI: Undo survives in-flight acceptance and new replies, replaced on acceptance, cleared on edits')

            # Every adapter gets bad key, quota, offline, malformed output, cancellation and timeout.
            for provider in ('gemini', 'openai', 'claude'):
                choose(provider); save_settings()
                for mode, pattern in ((400 if provider == 'gemini' else 401, r'key|accept'), (429, r'wait|minute|quota'),
                                      ('offline', r'connect|offline|internet|reach'),
                                      ('success', r'JSON|format|read')):
                    write(mode, 'not JSON at all' if mode == 'success' else None); wait_done()
                    expect(page.locator('#ai-write-status')).to_contain_text(re.compile(pattern, re.I))
                    assert values() == before
                    leak_check()
                count = len(calls)
                write('hold')
                expect(page.locator('#ai-write-button')).to_contain_text('Working')
                # DOM-dispatched clicks exercise the guard even when buttons are disabled.
                page.locator('#ai-write-button').dispatch_event('click')
                assert len(calls) == count + 1, 'Duplicate in-flight request'
                page.locator('#ai-cancel-button').click(); wait_done()
                expect(page.locator('#ai-write-status')).to_contain_text(re.compile('cancel', re.I))
                assert values() == before
                # Real timer verification: do not replace application timeout or AbortController.
                write('hold'); wait_done()
                expect(page.locator('#ai-write-status')).to_contain_text(re.compile('timed out|30 seconds', re.I))
                assert values() == before
                leak_check()
                print(f'PASS AI {provider}: bad key, quota, offline, malformed JSON, single-flight cancel, real 30s timeout')

            choose('gemini'); save_settings()
            for mode, pattern in ((403, 'key|permission|access'), (404, 'model'), (503, 'try|busy|unavailable'),
                                  ('blocked', 'blocked|safety'), ('empty', 'empty|answer|blocked'),
                                  ('partial_blocked', 'blocked|safety'), ('invalid_response', 'JSON')):
                write(mode); wait_done()
                expect(page.locator('#ai-write-status')).to_contain_text(re.compile(pattern, re.I))
                assert values() == before
                leak_check()
            write(text='```json\n' + json.dumps(SUGGESTION) + '\n```'); wait_done()
            expect(page.locator('[data-ai-field="headline"] .ai-suggested')).to_have_text(SUGGESTION['headline'])
            for invalid in ({'headline': 'Missing other fields'}, {**SUGGESTION, 'body': None}):
                write(text=json.dumps(invalid)); wait_done()
                expect(page.locator('#ai-write-status')).to_contain_text('JSON')
                assert values() == before
            long_text = {field: 'A' * 600 for field in FIELDS}
            write(text=json.dumps(long_text)); wait_done()
            for field, limit in zip(FIELDS, (140, 180, 450, 100)):
                assert len(page.locator(f'[data-ai-field="{field}"] .ai-suggested').text_content()) == limit
            # Unknown keys exercise regex redaction, independently of exact-key removal.
            for unknown in UNKNOWN_KEYS:
                assert unknown != FAKE_KEY
                write(text=json.dumps({field: 'Echo ' + unknown for field in FIELDS})); wait_done()
                for field in FIELDS:
                    expect(page.locator(f'[data-ai-field="{field}"] .ai-suggested')).to_have_text('Echo [key removed]')
                    page.locator(f'[data-ai-use="{field}"]').click()
                    expect(page.locator('#' + field)).to_have_value('Echo [key removed]')
                    page.locator('#ai-undo').click()
                    assert values() == before
                page.locator('[data-ai-use-all]').click()
                page.wait_for_function('''() => JSON.parse(localStorage.getItem('cultureshyft.factory.draft.v1'))
                  .payload.values.cta === 'Echo [key removed]' ''')
                page.locator('#save-brief').click()
                with page.expect_download() as download:
                    page.locator('#export-brief').click()
                download.value.save_as(str(exported))
                surfaces = page.content() + json.dumps(values()) + exported.read_text(encoding='utf-8')
                surfaces += page.evaluate('JSON.stringify(localStorage) + JSON.stringify(sessionStorage)')
                surfaces += '\n'.join(console + errors)
                assert unknown not in surfaces, 'Unknown provider key escaped redaction'
                page.locator('#ai-undo').click()
                assert values() == before
            print('PASS AI: unknown Gemini/OpenAI/project/Anthropic/OpenRouter keys redacted in all fields through acceptance/storage/export')

            # Script and HTML in EVERY field stay text through individual/all acceptance.
            markup = '<script>window.__aiHostile=1</script><img src=x onerror="window.__aiHostile=1">'
            script_count = page.locator('script').count()
            hostile = {field: markup + FAKE_KEY for field in FIELDS}
            write(text=json.dumps(hostile)); wait_done()
            leak_check()
            for field in FIELDS:
                expect(page.locator(f'[data-ai-field="{field}"] .ai-suggested')).to_have_text(markup + '[key removed]')
                page.locator(f'[data-ai-use="{field}"]').click()
                expect(page.locator('#' + field)).to_have_value(markup + '[key removed]')
                assert page.locator('script').count() == script_count
                assert page.locator('img[src="x"], [onerror]').count() == 0
                assert page.evaluate('window.__aiHostile === undefined')
                leak_check()
                page.locator('#ai-undo').click()
                assert values() == before
            page.locator('[data-ai-use-all]').click()
            assert all(values()[field] == markup + '[key removed]' for field in FIELDS)
            assert page.locator('script').count() == script_count
            assert page.locator('img[src="x"], [onerror]').count() == 0
            assert page.evaluate('window.__aiHostile === undefined')
            leak_check()
            page.locator('#ai-undo').click()
            assert values() == before
            print('PASS AI Gemini: errors, fences, maxlengths, configured key echo, script/HTML in every field through acceptance')

            # Dialog keyboard containment and touch layout at iPad and narrow phone widths.
            open_settings()
            for width, height in ((1024, 1366), (390, 844)):
                resize(page, width, height)
                for selector in ('#ai-provider', '#ai-api-key', '#ai-show-key', '#ai-test-connection', '#ai-save-settings'):
                    box = page.locator(selector).bounding_box()
                    assert box and box['height'] >= 44 and box['width'] >= 44, selector
                assert page.locator('#ai-settings-dialog').evaluate('e => e.scrollWidth <= e.clientWidth + 1')
                page.screenshot(path=str(output_dir / f'ai-settings-{width}.png'))
                for _ in range(15):
                    page.keyboard.press('Tab')
                    # Native dialogs may cycle through browser chrome (body is
                    # then active); no background page control may gain focus.
                    assert page.evaluate("document.activeElement === document.body || document.activeElement.closest('#ai-settings-dialog') !== null")
                page.locator('#headline').evaluate('e => e.focus()')
                expect(page.locator('#headline')).not_to_be_focused()
            page.keyboard.press('Escape')
            expect(page.locator('#open-ai-settings')).to_be_focused()
            page.set_viewport_size({'width': 1024, 'height': 1366})

            # Padded credentials remain usable, so Forget must match their trimmed
            # values in settings memory and both storage types (including targets).
            page.evaluate('''k => {
              const saved = JSON.parse(localStorage.getItem(k));
              saved.keys.openai = '  ' + saved.keys.gemini + '  ';
              saved.keys.claude = '\\t' + saved.keys.gemini + '\\t';
              saved.keys.local = ' ' + saved.keys.gemini;
              localStorage.setItem(k, JSON.stringify(saved));
              saved.keys.gemini = '  session-' + 'TEST'.repeat(8) + '\\t';
              saved.keys.local = saved.keys.gemini.trim();
              saved.keys.openrouter = '\\t' + saved.keys.openrouter + ' ';
              sessionStorage.setItem(k, JSON.stringify(saved));
              sessionStorage.setItem('ai-unrelated-test', 'keep me');
            }''', AI_KEY)
            page.reload(); ready()
            open_settings()
            page.locator('#ai-forget-key').click()
            assert FAKE_KEY in page.evaluate('(k) => localStorage.getItem(k)', AI_KEY)
            page.locator('#ai-forget-confirm-yes').click()
            expect(page.locator('#ai-settings-status')).to_contain_text('All matching provider copies were removed')
            for label in ('Gemini', 'OpenAI', 'Claude', 'OpenRouter', 'Local AI'):
                expect(page.locator('#ai-settings-status')).to_contain_text(label)
            for storage in ('localStorage', 'sessionStorage'):
                stored = json.loads(page.evaluate(f'(k) => {storage}.getItem(k)', AI_KEY))
                assert FAKE_KEY not in json.dumps(stored)
                assert not any(stored['keys'].values())
            assert page.evaluate("sessionStorage.getItem('ai-unrelated-test')") == 'keep me'
            expect(page.locator('#ai-api-key')).to_have_value('')
            for provider in ('openai', 'claude', 'openrouter', 'gemini'):
                page.locator('#ai-provider').select_option(provider)
                expect(page.locator('#ai-api-key')).to_have_value('')
            # Reopening copies settings memory back into dialog memory; saving
            # must not resurrect a forgotten copy in another provider slot.
            page.keyboard.press('Escape')
            open_settings()
            for provider in ('openai', 'claude', 'openrouter', 'gemini'):
                page.locator('#ai-provider').select_option(provider)
                expect(page.locator('#ai-api-key')).to_have_value('')
            save_settings()
            assert FAKE_KEY not in page.evaluate('(k) => localStorage.getItem(k)', AI_KEY)
            count = len(calls)
            page.reload(); ready()
            assert len(calls) == count
            page.locator('#ai-write-button').click()
            expect(page.locator('#ai-settings-dialog')).to_be_visible()
            page.keyboard.press('Escape')
            print('PASS AI: accessible modal/touch targets, padded copies forgotten in memory/local/session storage and reload recovery')

            # Distinct credentials are preserved; unsaved dialog copies are forgotten.
            choose('gemini'); save_settings()
            choose('claude')
            distinct_key = 'different-' + 'TEST' * 8
            page.locator('#ai-api-key').fill(distinct_key)
            save_settings()
            choose('openai')
            page.locator('#ai-api-key').fill('  ' + FAKE_KEY + '\t')
            page.locator('#ai-provider').select_option('claude')
            save_settings()  # Saving another provider preserves the padded value.
            open_settings()
            page.locator('#ai-provider').select_option('openai')
            expect(page.locator('#ai-api-key')).to_have_value('  ' + FAKE_KEY + '\t')
            choose('openrouter')  # Another padded copy exists only in dialog memory.
            page.locator('#ai-api-key').fill('\t' + FAKE_KEY + ' ')
            page.locator('#ai-provider').select_option('gemini')
            page.locator('#ai-forget-key').click()
            page.locator('#ai-forget-confirm-yes').click()
            page.locator('#ai-provider').select_option('openai')
            expect(page.locator('#ai-api-key')).to_have_value('')
            page.locator('#ai-provider').select_option('openrouter')
            expect(page.locator('#ai-api-key')).to_have_value('')
            page.locator('#ai-provider').select_option('claude')
            expect(page.locator('#ai-api-key')).to_have_value(distinct_key)
            stored = json.loads(page.evaluate('(k) => localStorage.getItem(k)', AI_KEY))
            assert FAKE_KEY not in json.dumps(stored)
            assert stored['keys']['claude'] == distinct_key
            page.keyboard.press('Escape')
            print('PASS AI: forget clears padded unsaved dialog copies and preserves distinct provider keys')

            # Local failures explain exact server fixes, with no cloud key attached.
            choose('local'); save_settings()
            write('offline'); wait_done()
            status = page.locator('#ai-write-status').inner_text()
            for fragment in ('Enable CORS', 'Developer', 'Start server', 'OLLAMA_ORIGINS=https://cultureshyftmedia.com', 'restart Ollama', 'Safari', 'iPad', 'Gemini'):
                assert fragment in status, fragment
            validate_request('local', calls[-1])
            leak_check()

            # Credentials cannot become a model/URL, and local URL errors are
            # resolved before fetch. Settings test shares the cancellation guard.
            open_settings()
            count = len(calls)
            page.locator('#ai-model').fill(FAKE_KEY)
            page.locator('#ai-test-connection').click()
            expect(page.locator('#ai-settings-status')).to_contain_text('model')
            assert len(calls) == count
            page.locator('#ai-model').fill(PROVIDERS['local'][1])
            for invalid_url in ('javascript:alert(1)', 'http://user:password@localhost:1234/v1',
                                'http://localhost:1234/v1?key=' + FAKE_KEY,
                                'http://localhost:1234/v1#secret'):
                page.locator('#ai-base-url').fill(invalid_url)
                page.locator('#ai-test-connection').click()
                expect(page.locator('#ai-settings-status')).to_contain_text('base URL')
                assert len(calls) == count
            page.locator('#ai-base-url').fill('http://localhost:1234/v1')
            mock['mode'] = 'hold'
            page.locator('#ai-test-connection').click()
            expect(page.locator('#ai-test-connection')).to_have_text('Working...')
            page.locator('#ai-test-connection').dispatch_event('click')
            expect(page.locator('#ai-settings-status')).to_contain_text('already working')
            assert len(calls) == count + 1
            # The rejected second tap must not orphan the first test's result.
            page.locator('#ai-test-cancel-button').click()
            expect(page.locator('#ai-settings-status')).to_contain_text('Cancelled')
            page.keyboard.press('Escape')
            leak_check()
            print('PASS AI: unsafe URL/model rejection, connection-test cancellation and single flight')

            # Customer page must have neither UI nor AI resources.
            count = len(calls)
            page.goto((checks.ROOT / 'docs/order/index.html').as_uri()); ready()
            assert not page.locator('script[src$="ai.js"], link[href$="ai.css"], #open-ai-settings, #ai-write-button, #ai-settings-dialog').count()
            assert 'Write it for me' not in page.locator('body').inner_text()
            assert len(calls) == count
            print('PASS AI: local server guidance, order page isolation, no unsolicited requests')

            # Storage blocked and quota-full both retain usable settings for this session.
            for failure in ('blocked', 'full'):
                recovery = context.new_page()
                recovery.on('pageerror', lambda error: errors.append(str(error)))
                recovery.on('console', lambda msg: console.append(msg.text))
                recovery.add_init_script('''(() => {
                  const originalGet = Storage.prototype.getItem;
                  const originalSet = Storage.prototype.setItem;
                  Storage.prototype.getItem = function(k) {
                    if (k === 'cultureshyft.factory.ai.v1') {
                      if (BLOCKED) throw new DOMException('blocked', 'SecurityError');
                      return null;
                    }
                    return originalGet.call(this, k);
                  };
                  Storage.prototype.setItem = function(k, v) {
                    if (k === 'cultureshyft.factory.ai.v1') throw new DOMException('full', 'QuotaExceededError');
                    return originalSet.call(this, k, v);
                  };
                })();'''.replace('BLOCKED', 'true' if failure == 'blocked' else 'false'))
                main_page, page = page, recovery
                page.goto(checks.FACTORY_PAGE.as_uri()); ready()
                choose('gemini')
                page.locator('#ai-save-settings').click()
                expect(page.locator('#ai-settings-dialog')).to_be_visible()
                expect(page.locator('#ai-storage-warning')).to_contain_text(re.compile('session|open|memory', re.I))
                page.locator('#ai-close-settings').click()
                write(); wait_done()
                expect(page.locator('#ai-suggestions')).to_be_visible()
                open_settings()
                expect(page.locator('#ai-api-key')).to_have_value(FAKE_KEY)
                page.keyboard.press('Escape')
                leak_check()
                page.close(); page = main_page
                print(f'PASS AI: {failure} storage, session fallback, warning, usable generation')

            # Forget cancels a held connection test. After its rejection settles,
            # the removal report must survive, including blocked-storage warnings.
            # Failed storage updates fall back to removal or report failure honestly.
            page.goto(checks.FACTORY_PAGE.as_uri()); ready()
            for failure in ('normal', 'write-fails', 'removal-blocked'):
                choose('gemini'); save_settings()
                choose('openai'); save_settings()
                page.evaluate('''({k, failure}) => {
                  sessionStorage.setItem(k, localStorage.getItem(k));
                  window.aiOriginalSet = Storage.prototype.setItem;
                  window.aiOriginalRemove = Storage.prototype.removeItem;
                  Storage.prototype.setItem = function(key, value) {
                    if (key === k && failure !== 'normal') throw new DOMException('full', 'QuotaExceededError');
                    return window.aiOriginalSet.call(this, key, value);
                  };
                  Storage.prototype.removeItem = function(key) {
                    if (key === k && failure === 'removal-blocked') throw new DOMException('blocked', 'SecurityError');
                    return window.aiOriginalRemove.call(this, key);
                  };
                }''', {'k': AI_KEY, 'failure': failure})
                open_settings()
                mock['mode'] = 'hold'
                held_count = len(held)
                page.locator('#ai-test-connection').click()
                expect(page.locator('#ai-test-connection')).to_have_text('Working...')
                assert len(held) == held_count + 1, 'Connection test was not intercepted and held'
                page.locator('#ai-forget-key').click()
                page.locator('#ai-forget-confirm-yes').click()
                expect(page.locator('#ai-test-connection')).to_be_enabled()
                expect(page.locator('#ai-test-connection')).to_have_text('Test connection')
                expect(page.locator('#ai-test-cancel-button')).to_be_hidden()
                expected = {'normal': 'All matching provider copies were removed',
                            'write-fails': 'saved AI settings were removed',
                            'removal-blocked': 'blocked removal'}[failure]
                expect(page.locator('#ai-settings-status')).to_contain_text(expected)
                for storage in ('localStorage', 'sessionStorage'):
                    saved = page.evaluate(f'(k) => {storage}.getItem(k)', AI_KEY)
                    if failure == 'normal':
                        assert saved is not None and FAKE_KEY not in saved
                        stored_keys = json.loads(saved)['keys']
                        assert not stored_keys.get('gemini') and not stored_keys.get('openai')
                    else:
                        assert (FAKE_KEY in saved) if failure == 'removal-blocked' else saved is None
                # Recheck after storage inspection, beyond the cancelled fetch's
                # promise handlers, rather than accepting a transient success.
                expect(page.locator('#ai-settings-status')).to_contain_text(expected)
                for provider in ('gemini', 'openai'):
                    page.locator('#ai-provider').select_option(provider)
                    expect(page.locator('#ai-api-key')).to_have_value('')
                page.keyboard.press('Escape')
                open_settings()
                expect(page.locator('#ai-api-key')).to_have_value('')
                page.keyboard.press('Escape')
                page.evaluate('''() => {
                  Storage.prototype.setItem = window.aiOriginalSet;
                  Storage.prototype.removeItem = window.aiOriginalRemove;
                }''')
                # Clean up the deliberately retained fixture using the real UI.
                open_settings()
                page.locator('#ai-forget-key').click()
                page.locator('#ai-forget-confirm-yes').click()
                page.keyboard.press('Escape')
                print(f'PASS AI: forget {failure} during held connection test, memory cleared and removal report preserved')
            assert not errors, errors
        except Exception as exc:
            raise checks.CheckFailure(f'AI helper: {exc}') from exc
        finally:
            # Settle held (often already-cancelled) requests so closing the
            # browser does not leave Playwright route handlers pending.
            while held:
                try:
                    held.pop().abort()
                except Exception:
                    pass
            context.close()
    print('PASS AI helper: all mocked provider and safety checks (none skipped)')


if __name__ == '__main__':
    import check_factory as checks
    checks.SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    output = checks.SCRATCH_DIR / f'ai-evidence-{uuid.uuid4().hex}'
    check_ai(checks.DEFAULT_CHROME, output)
