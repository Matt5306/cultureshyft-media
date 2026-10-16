"""Real phone viewport and user-flow checks used by check_factory.py.

Uses the installed Chrome, isolated workspace storage, and file URLs only.
No server, credentials, external requests, or browser installation is needed.
"""
from __future__ import annotations

import io
import json
import sys
import uuid
from pathlib import Path

from PIL import Image, ImageDraw


def check_browser(chrome: Path, output_dir: Path) -> None:
    # Reuse the running entry point's exception class when invoked by acceptance.
    checks = sys.modules.get("__main__")
    if not hasattr(checks, "_check_report_details"):
        import check_factory as checks
    try:
        from playwright.sync_api import sync_playwright, expect
    except ImportError as exc:
        raise checks.CheckFailure("Phone checks require the installed Python playwright package; no browser download is needed.") from exc

    profile = checks.SCRATCH_DIR / f"phone-profile-{uuid.uuid4().hex}"
    profile.mkdir(parents=True)
    failures: list[str] = []
    external: list[str] = []
    try:
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(
                str(profile), executable_path=str(chrome), headless=True,
                viewport={"width": 390, "height": 844}, device_scale_factor=1,
                accept_downloads=True,
                args=["--no-sandbox", "--disable-gpu", "--disable-background-networking",
                      "--disable-component-update", "--allow-file-access-from-files", "--window-size=390,844"],
            )
            try:
                def route_request(route):
                    if route.request.url.startswith(("http:", "https:")):
                        external.append(route.request.url)
                        route.abort()
                    else:
                        route.continue_()
                context.route("**/*", route_request)
                page = context.pages[0] if context.pages else context.new_page()
                page.on("pageerror", lambda error: failures.append(str(error)))
                page.on("console", lambda message: failures.append(message.text) if message.type == "error" else None)
                page.on("dialog", lambda dialog: (failures.append("Native dialog used"), dialog.dismiss()))

                def ready():
                    page.evaluate("() => window.factoryReady")
                    page.wait_for_function("window.factoryReport && window.factoryReport().ready")

                for demo in checks.DEMOS:
                    page.goto(checks._page_url(demo), wait_until="load")
                    ready()
                    report = page.evaluate("window.factoryReport()")
                    if report["missing"] or report["overflow"]:
                        raise checks.CheckFailure(f"{demo} 390px: {report}")
                    checks._check_report_details(report, demo, f"{demo} phone", 390)
                    assert report["diagnostics"]["viewportWidth"] == 390, "Phone check must use a real 390px viewport"
                    page.locator("#preview-well").scroll_into_view_if_needed()
                    preview = page.locator("#flyer").bounding_box()
                    assert preview and preview["x"] >= 0 and preview["x"] + preview["width"] <= 391
                    for selector in ("#mobile-print", "#mobile-download"):
                        box = page.locator(selector).bounding_box()
                        assert box and box["width"] >= 44 and box["height"] >= 44
                        assert box["y"] >= 0 and box["y"] + box["height"] <= 845
                    path = output_dir / f"{demo}-mobile.png"
                    page.screenshot(path=str(path))
                    checks._check_screenshot(path, checks.MOBILE_SIZE, f"{demo} phone")
                    print(f"PASS {demo}: true 390x844 viewport, visible preview, 44px sticky actions")

                page.goto(checks.FACTORY_PAGE.as_uri() + "?check=1", wait_until="load")
                ready()
                page.locator("#headline").fill("Phone recovery check")
                page.locator("#contact").fill("mark@example.com")
                page.wait_for_function("document.getElementById('save-status').textContent.includes('Saved')")
                page.reload(wait_until="load")
                ready()
                expect(page.locator("#headline")).to_have_value("Phone recovery check")
                expect(page.locator("#contact")).to_have_value("mark@example.com")

                # A generated, strongly asymmetric image makes crop movement measurable.
                photo = Image.new("RGB", (1200, 800), "#ff5a1f")
                draw = ImageDraw.Draw(photo)
                draw.rectangle((0, 0, 300, 800), fill="#14151a")
                draw.rectangle((900, 0, 1200, 800), fill="#ffffff")
                data = io.BytesIO()
                photo.save(data, format="PNG")
                page.locator("#photo").set_input_files({"name": "crop-check.png", "mimeType": "image/png", "buffer": data.getvalue()})
                page.wait_for_function("window.factoryPhoto.getState().dataUrl && document.getElementById('flyer-photo').naturalWidth > 0")
                page.locator("#photo-zoom").focus()
                page.locator("#photo-zoom").press("End")
                # Center it so the sticky 44px action bar cannot cover the drag point.
                page.locator("#photo-area").evaluate("el => el.scrollIntoView({block: 'center'})")
                area = page.locator("#photo-area").bounding_box()
                assert area
                before = page.evaluate("window.factoryPhoto.getState()")
                x, y = area["x"] + area["width"] / 2, area["y"] + area["height"] / 2
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x - 35, y + 12, steps=5)
                page.mouse.up()
                after = page.evaluate("window.factoryPhoto.getState()")
                assert after["zoom"] == 2.5 and after["focusX"] != before["focusX"], "Drag and zoom must affect crop"
                page.locator("#qr-url").fill("https://cultureshyftmedia.com/")
                page.locator("#save-brief").click()
                page.reload(wait_until="load")
                ready()
                page.wait_for_function("document.getElementById('flyer-photo').naturalWidth > 0")
                restored = page.evaluate("window.factoryPhoto.getState()")
                assert restored == after, "Photo bytes and exact crop must survive reload"
                for mode in checks.SOCIAL_SIZES:
                    page.evaluate("mode => window.factoryRenderSocial(mode)", mode)
                social = page.evaluate("window.factorySocialDiagnostics()")
                assert all(value["photoUsed"] for value in social.values()), "All social outputs must use the photo"
                for value in social.values():
                    assert abs(value["crop"]["focusX"] - after["focusX"]) < 0.0001, "Social crop must follow preview"
                assert social["story"].get("qrBox"), "Story must render QR"

                with page.expect_download() as download:
                    page.locator("#export-brief").click()
                exported_path = output_dir / "recovery-brief.json"
                download.value.save_as(str(exported_path))
                exported = json.loads(exported_path.read_text(encoding="utf-8"))
                assert exported["payload"]["photo"] == after
                page.locator("#headline").fill("Temporary edit")
                page.locator("#import-brief").set_input_files(str(exported_path))
                expect(page.locator("#headline")).to_have_value("Phone recovery check")
                page.locator("#import-brief").set_input_files({"name": "damaged.json", "mimeType": "application/json", "buffer": b'{"payload":false}'})
                expect(page.locator("#save-status")).to_contain_text("unchanged")
                expect(page.locator("#headline")).to_have_value("Phone recovery check")
                page.locator("#save-brief").click()

                page.locator("#open-briefs").click()
                cards = page.locator(".brief-card")
                count = cards.count()
                assert count >= 1
                cards.first.get_by_role("button", name="Duplicate", exact=True).click()
                expect(cards).to_have_count(count + 1)
                cards.first.get_by_role("button", name="Delete", exact=True).click()
                expect(cards).to_have_count(count + 1)
                cards.first.get_by_role("button", name="Keep it", exact=True).click()
                expect(cards).to_have_count(count + 1)
                cards.first.get_by_role("button", name="Delete", exact=True).click()
                cards.first.get_by_role("button", name="Remove", exact=True).click()
                expect(cards).to_have_count(count)
                cards.first.get_by_role("button", name="Open", exact=True).click()
                expect(page.locator("#headline")).to_have_value("Phone recovery check")

                # Browser storage failure must preserve the previous saved bytes.
                prior = page.evaluate("JSON.stringify({...localStorage})")
                page.evaluate("() => { Storage.prototype.setItem = function() { throw new DOMException('Full', 'QuotaExceededError'); }; }")
                page.locator("#headline").fill("Keep this unsaved edit")
                expect(page.locator("#save-status")).to_contain_text("export", ignore_case=True)
                assert page.evaluate("JSON.stringify({...localStorage})") == prior
                expect(page.locator("#headline")).to_have_value("Keep this unsaved edit")
                assert not failures, f"Browser console errors: {failures}"
                assert not external, f"Unexpected network requests: {external}"
                print("PASS saved briefs: reload, photo/crop, export/import, duplicate, in-page delete, quota recovery; no console errors or external requests")
            finally:
                context.close()
    except checks.CheckFailure:
        raise
    except Exception as exc:
        raise checks.CheckFailure(f"Phone/user-flow browser checks could not pass: {exc}") from exc


if __name__ == "__main__":
    import check_factory as checks
    output = checks.SCRATCH_DIR / f"browser-check-{uuid.uuid4().hex}"
    output.mkdir(parents=True)
    check_browser(checks.DEFAULT_CHROME, output)
