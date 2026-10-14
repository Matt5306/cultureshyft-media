"""Order, shared-brief and invoice acceptance; local Chrome, no external requests."""
import base64
import json
import sys
import uuid
from urllib.parse import urlparse, parse_qs


def check_orders(chrome, output_dir):
    checks = sys.modules.get('__main__')
    if not hasattr(checks, '_check_pdf'):
        import check_factory as checks
    from playwright.sync_api import sync_playwright, expect
    errors, network = [], []
    with sync_playwright() as pw:
        profile = checks.SCRATCH_DIR / f'orders-{uuid.uuid4().hex}'
        profile.mkdir()
        context = pw.chromium.launch_persistent_context(str(profile), executable_path=str(chrome), headless=True,
            viewport={'width': 1440, 'height': 1200}, args=['--no-sandbox', '--disable-gpu', '--disable-background-networking', '--disable-component-update', '--allow-file-access-from-files'])
        def route_request(route):
            if route.request.url.startswith(('http:', 'https:')):
                network.append(route.request.url)
                route.abort()
            else:
                route.continue_()
        context.route('**/*', route_request)
        page = context.pages[0]
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
        def ready():
            page.evaluate('() => window.factoryReady')
        try:
            order_url = (checks.ROOT / 'docs/order/index.html').as_uri() + '?demo=community-event&check=1'
            page.goto(order_url); ready()
            page.locator('#clientName').fill('Renée & Community')
            page.locator('#clientEmail').fill('renee@example.com')
            page.locator('#extraSizes').select_option('2')
            page.locator('#rush').check()
            payload = page.evaluate('window.factoryBrief.collect()')
            prepared = page.evaluate('window.factoryOrder.update()')
            assert prepared['mailto'].startswith('mailto:mark@cultureshyftmedia.com?')
            mail = parse_qs(urlparse(prepared['mailto']).query)
            assert 'Renée & Community' in mail['body'][0] and prepared['link'] in mail['body'][0]
            assert '$45.00' in page.locator('#order-total').inner_text()
            for size, suffix in [(checks.DESKTOP_SIZE, 'desktop'), (checks.MOBILE_SIZE, 'mobile')]:
                page.set_viewport_size({'width': size[0], 'height': size[1]})
                report = page.evaluate('window.factoryReport()')
                assert not report['overflow'] and not report['missing'], report
                checks._check_report_details(report, 'community-event', 'order ' + suffix, size[0])
                path = output_dir / f'order-{suffix}.png'
                page.screenshot(path=str(path)); checks._check_screenshot(path, size, 'order ' + suffix)
            order_pdf = output_dir / 'order-letter.pdf'
            page.pdf(path=str(order_pdf), prefer_css_page_size=True, print_background=True)
            checks._check_pdf(order_pdf, 'order')
            # Oversized Unicode grows after UTF-8/base64 and must preserve the text fallback.
            fallback = page.evaluate('''() => {
              const p = factoryBrief.collect();
              for (const key of ['headline','subheadline','date','place','body','cta','contact','clientName','clientEmail']) {
                const max = document.querySelector(`[name="${key}"]`).maxLength;
                p.values[key] = '界'.repeat(max);
              }
              return factoryOrder.prepare(p);
            }''')
            assert fallback['reason'] and not fallback['mailto'] and '界' in fallback['text']
            assert page.evaluate("() => { try { factoryShare.decode('bad!'); return false; } catch (_) { return true; } }")
            # Clipboard rejection must give an actionable manual fallback.
            page.evaluate("Object.defineProperty(navigator, 'clipboard', {value: {writeText: () => Promise.reject(new Error('blocked'))}, configurable:true})")
            page.locator('#copy-order').click()
            expect(page.locator('#order-status')).to_contain_text('Use Copy')
            parsed_link = urlparse(prepared['link'])
            assert not parsed_link.query, 'Generated customer link must keep the brief out of the server-visible query'
            token = parse_qs(parsed_link.fragment)['brief'][0]
            assert payload['values']['clientName'] not in parsed_link.query and payload['values']['clientEmail'] not in parsed_link.query
            page.goto(checks.FACTORY_PAGE.as_uri() + '?check=1#brief=' + token); ready()
            actual = page.evaluate('window.factoryBrief.collect()')
            assert actual == payload, f'Brief round-trip differs: {actual} != {payload}'
            expect(page.locator('#preset-status')).to_contain_text('Customer brief loaded')
            legacy_payload = json.loads(json.dumps(payload))
            legacy_payload['values']['headline'] = 'Legacy query link'
            legacy_token = page.evaluate('(payload) => factoryShare.encode(payload)', legacy_payload)
            page.goto(checks.FACTORY_PAGE.as_uri() + '?brief=' + legacy_token + '&check=1'); ready()
            assert page.evaluate('window.factoryBrief.collect()') == legacy_payload, 'Legacy ?brief= link did not load'
            page.goto(checks.FACTORY_PAGE.as_uri() + '?brief=' + legacy_token + '&check=1#brief=' + token); ready()
            page.reload(); ready()
            assert page.evaluate('window.factoryBrief.collect()') == payload, 'Fragment brief must take precedence over legacy query brief'
            page.locator('#make-invoice').click()
            state = page.evaluate('window.factoryInvoice.getState()')
            assert state['clientName'] == payload['values']['clientName'] and state['clientEmail'] == payload['values']['clientEmail'], state
            assert state['totals'] == {'subtotal':45, 'total':45, 'deposit':22.5, 'balance':22.5}, state
            print('PASS order: desktop/phone/PDF, readable email, fragment brief round-trip, legacy query fallback and fragment precedence, oversize/copy fallbacks, invoice from brief')
            page.goto(checks._page_url('invoice')); ready()
            payment_text = page.locator('#invoice-payment-view').inner_text()
            assert '$YourCashtag' in payment_text and 'you@example.com' in payment_text and 'paypal.me/YourName' in payment_text, payment_text
            assert '$CultureShyft' not in payment_text and 'paypal.me/CultureShyft' not in payment_text, payment_text
            for size, suffix in [(checks.DESKTOP_SIZE, 'desktop'), (checks.MOBILE_SIZE, 'mobile')]:
                page.set_viewport_size({'width':size[0], 'height':size[1]})
                report = page.evaluate('window.factoryReport()')
                assert not report['overflow'] and not report['missing'], report
                checks._check_report_details(report, 'invoice', 'invoice ' + suffix, size[0])
                page.locator('#invoice-preview-well').scroll_into_view_if_needed()
                path = output_dir / f'invoice-{suffix}.png'
                page.screenshot(path=str(path)); checks._check_screenshot(path, size, 'invoice ' + suffix)
            math = page.evaluate('''() => factoryInvoice.calculate([{unitPrice:20,quantity:1},{unitPrice:5,quantity:3},{unitPrice:10,quantity:1},{unitPrice:15,quantity:1}])''')
            assert math == {'subtotal':60,'total':60,'deposit':30,'balance':30}, math
            odd = page.evaluate('factoryInvoice.calculate([{unitPrice:0.05,quantity:1}])')
            assert odd == {'subtotal':.05,'total':.05,'deposit':.03,'balance':.02}, odd
            state = page.evaluate('factoryInvoice.getState()')
            total = sum(line['quantity'] * line['unitPrice'] for line in state['lines'])
            assert total == 50 and state['totals'] == {'subtotal':50,'total':50,'deposit':25,'balance':25}, state
            assert '$50.00' in page.locator('#invoice-page').inner_text()
            png = page.evaluate('() => factoryInvoice.renderReceipt()')
            receipt = output_dir / 'invoice-receipt.png'
            receipt.write_bytes(base64.b64decode(png.split(',')[1]))
            checks._check_screenshot(receipt, (1080,1350), 'invoice receipt')
            # Recovery and settings run in this isolated browser profile only.
            page.goto(checks.FACTORY_PAGE.as_uri() + '#brief=' + token); ready()
            page.locator('#make-invoice').click()
            page.locator('#invoice-notes').fill('Keep this invoice edit when I return.')
            number = page.locator('#invoice-number').input_value()
            page.locator('#invoice-close').click()
            page.locator('#make-invoice').click()
            expect(page.locator('#invoice-notes')).to_have_value('Keep this invoice edit when I return.')
            expect(page.locator('#invoice-number')).to_have_value(number)
            page.locator('#invoice-settings-open').click()
            page.locator('#invoice-cashapp').fill('$YourCashtag')
            page.locator('#invoice-paypal').fill('https://invalid.example/pay')
            page.locator('#invoice-settings-form button[type=submit]').click()
            expect(page.locator('#invoice-settings-status')).to_contain_text('Fix')
            page.locator('#invoice-paypal').fill('https://paypal.me/YourName')
            page.locator('#invoice-settings-form button[type=submit]').click()
            expect(page.locator('#invoice-settings')).to_be_hidden()
            assert 'https://paypal.me/YourName' in page.evaluate('factoryInvoice.report().diagnostics.paymentLinks')
            draft = page.evaluate("localStorage.getItem('csm.invoice.draft.v1')")
            page.reload(); ready()
            assert page.evaluate("localStorage.getItem('csm.invoice.draft.v1')") == draft, 'Opening factory must not overwrite invoice draft'
            page.evaluate("localStorage.setItem('csm.invoice.counter.v1', '{damaged')")
            page.reload(); ready()
            page.locator('#make-invoice').click()
            assert page.evaluate("localStorage.getItem('csm.invoice.counter.v1')") == '{damaged'
            assert page.locator('#invoice-number').input_value().endswith('-??')
            assert page.evaluate('factoryInvoice.report().missing'), 'Damaged numbering must block export'
            print('PASS invoice recovery: preserves edits/draft, validates all payment settings, preserves damaged counter and requires manual recovery')
            assert not errors, errors
            assert not network, network
            print('PASS invoice: desktop/phone, totals independently reconciled, cent rounding, 1080x1350 PNG, no console or network errors')
        finally:
            context.close()
