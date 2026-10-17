#!/usr/bin/env python3
"""Acceptance checks for the browser-only CultureShyft Flyer Factory.

The checker clicks the real PNG and PDF export buttons, intercepting only the
final print-dialog call for headless PDF capture. The page publishes its check
report as JSON when ``check=1`` is present. Installed Playwright polls that
report before reading the rendered DOM and sets a real 390px phone viewport
(Windows Chrome otherwise clamps command-line windows to 500px). No browser
download or server is used.

Run from anywhere::

    python tools/check_factory.py
    python tools/check_factory.py --keep
    python tools/check_factory.py --social

``--keep`` preserves the generated PNG and PDF evidence in
``tools/html/factory``.  Otherwise evidence and isolated browser profiles remain in the ignored
``tools/html/factory-tmp`` scratch folder for diagnosis (never auto-deleted).
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

try:
    from PIL import Image, ImageStat
except ImportError as exc:  # pragma: no cover - exercised on machines missing Pillow
    Image = ImageStat = None  # type: ignore[assignment]
    PIL_IMPORT_ERROR: ImportError | None = exc
else:
    PIL_IMPORT_ERROR = None

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover - exercised on machines missing pypdf
    PdfReader = None  # type: ignore[assignment,misc]
    PYPDF_IMPORT_ERROR: ImportError | None = exc
else:
    PYPDF_IMPORT_ERROR = None


ROOT = Path(__file__).resolve().parents[1]
FACTORY_PAGE = ROOT / "docs" / "factory" / "index.html"
DEFAULT_CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
KEEP_DIR = ROOT / "tools" / "html" / "factory"
SCRATCH_DIR = ROOT / "tools" / "html" / "factory-tmp"
PRESETS = json.loads((ROOT / "docs/factory/presets.json").read_text(encoding="utf-8"))
DEMOS = ("poster", "event", "announcement", "event-qr", *PRESETS)
DESKTOP_SIZE = (1440, 1200)
MOBILE_SIZE = (390, 844)
LETTER_POINTS = (612.0, 792.0)
SOCIAL_SIZES = {"square": (1080, 1080), "story": (1080, 1920), "facebook": (1920, 1005)}
REPORT_RE = re.compile(
    r'<script\b[^>]*\bid=["\']factory-check-report["\'][^>]*>(.*?)</script\s*>',
    re.IGNORECASE | re.DOTALL,
)
CONTACT_RE = re.compile(
    r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|@\w{3,}|"
    r"(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}|"
    r"(?:https?://|www\.)?\w[\w.-]+\.(?:com|org|net))",
    re.IGNORECASE,
)
OWNED_ARTIFACTS = frozenset(
    [f"{demo}-{view}.png" for demo in DEMOS for view in ("desktop", "mobile")]
    + [f"{demo}-letter.pdf" for demo in DEMOS]
    + [f"{demo}-{kind}.png" for demo in DEMOS for kind in SOCIAL_SIZES]
    + [f"{demo}-{view}.png" for demo in ("order", "invoice") for view in ("desktop", "mobile")]
    + ["order-letter.pdf", "invoice-letter.pdf", "invoice-receipt.png"]
    + [f"invoice-{failure}{suffix}" for failure in ("quota", "blocked") for suffix in ("-receipt.png", ".pdf")]
)


class CheckFailure(RuntimeError):
    """An acceptance condition failed with a user-actionable explanation."""


class _ResilientTemporaryDirectory:
    """Use inherited workspace permissions; retain scratch evidence for recovery.

    Python 3.13's private temporary-directory ACL can deny a child Chrome
    process access on Windows. An ordinary uniquely named workspace directory
    avoids that startup failure. No source or user data is removed.
    """

    def __init__(self, *, prefix: str, dir: Path, **_: object) -> None:
        self.path = Path(dir) / f"{prefix}{uuid.uuid4().hex}"
        self.path.mkdir(parents=True)

    def __enter__(self) -> str:
        return str(self.path)

    def __exit__(self, *_: object) -> None:
        pass


@dataclass(frozen=True)
class ChromeResult:
    stdout: str
    stderr: str


def _creation_flags() -> int:
    """Prevent a transient console window when invoked from desktop Python."""
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def _run_chrome(chrome: Path, profile: Path, args: list[str], label: str) -> ChromeResult:
    command = [
        str(chrome),
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-breakpad",
        "--disable-crash-reporter",
        "--hide-scrollbars",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-extensions",
        "--no-first-run",
        "--allow-file-access-from-files",
        "--force-device-scale-factor=1",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=15000",
        f"--user-data-dir={profile}",
        *args,
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            creationflags=_creation_flags(),
        )
    except subprocess.TimeoutExpired as exc:
        raise CheckFailure(f"{label}: Chrome did not finish within 45 seconds") from exc
    except OSError as exc:
        raise CheckFailure(f"{label}: could not start Chrome: {exc}") from exc

    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()[-2000:]
        raise CheckFailure(
            f"{label}: Chrome exited with code {completed.returncode}"
            + (f"\n{details}" if details else "")
        )
    return ChromeResult(completed.stdout, completed.stderr)


def _page_url(demo: str, social: bool = False) -> str:
    query = {"demo": "event" if demo == "event-qr" else demo, "check": "1"}
    if demo == "event-qr":
        query["qr"] = "1"
    if social:
        query["social"] = "1"
    return f"{FACTORY_PAGE.as_uri()}?{urlencode(query)}"


def _runtime_errors_from_dom(dumped_dom: str) -> list[str]:
    """Recover the page's own JavaScript diagnostics from a partial result."""
    matches = REPORT_RE.findall(dumped_dom)
    if not matches:
        return []
    try:
        report = json.loads(html.unescape(matches[-1]).strip())
        errors = report.get("diagnostics", {}).get("runtimeErrors", [])
        return [str(error) for error in errors] if isinstance(errors, list) else []
    except (AttributeError, json.JSONDecodeError, TypeError):
        return []


def _with_runtime_errors(message: str, dumped_dom: str) -> str:
    errors = _runtime_errors_from_dom(dumped_dom)
    return message + ("\nPage runtimeErrors:\n" + json.dumps(errors, indent=2, ensure_ascii=False) if errors else "\nPage runtimeErrors: []")


def _check_social(page: Any, output_dir: Path, demo: str) -> None:
    """Check PNGs downloaded through the same buttons used by customers."""
    for kind, size in SOCIAL_SIZES.items():
        label = f"{demo} {kind}"
        path = output_dir / f"{demo}-{kind}.png"
        with page.expect_download(timeout=15000) as download:
            page.locator(f'[data-social-export="{kind}"]').click()
        download.value.save_as(str(path))
        with Image.open(path) as image:
            image.load()
            if image.format != "PNG" or image.size != size:
                raise CheckFailure(f"{label}: expected PNG {size}, got {image.format} {image.size}")
            if image.convert("RGBA").getchannel("A").getextrema() != (255, 255):
                raise CheckFailure(f"{label}: export contains transparent pixels")
        _check_screenshot(path, size, label)
        layout = page.evaluate("window.factorySocialDiagnostics()").get(kind)
        _check_social_layout(layout, size, kind, label)
        if demo == "event-qr" and kind == "story" and not layout.get("qrBox"):
            raise CheckFailure(f"{label}: QR demo story did not render its QR code")


def _check_social_layout(layout: Any, size: tuple[int, int], kind: str, label: str) -> None:
    """Check the measured canvas text, including the story's protected top/bottom."""
    if not isinstance(layout, dict) or not isinstance(layout.get("fits"), dict):
        raise CheckFailure(f"{label}: missing measured canvas layout diagnostics")
    top, bottom = (250, size[1] - 250) if kind == "story" else (0, size[1])

    def check_box(box: Any, name: str) -> None:
        if not isinstance(box, dict) or any(
            isinstance(box.get(key), bool) or not isinstance(box.get(key), (int, float))
            or not math.isfinite(box[key]) for key in ("x", "y", "width", "height")
        ):
            raise CheckFailure(f"{label}: {name} has invalid bounds")
        if (box["width"] <= 0 or box["height"] <= 0 or box["x"] < 0 or box["y"] < top
                or box["x"] + box["width"] > size[0] + 0.5
                or box["y"] + box["height"] > bottom + 0.5):
            raise CheckFailure(f"{label}: {name} extends outside the canvas or story safe area")

    required = {"headline", "date", "place", "contact"}
    if kind == "story":
        required.update(("body", "cta"))
    fits = layout["fits"]
    if not required.issubset(fits):
        raise CheckFailure(f"{label}: required text measurements are missing")
    for name, fit in fits.items():
        check_box(fit.get("box"), name)
        if not fit.get("lines"):
            raise CheckFailure(f"{label}: demo {name} is empty")
        if fit.get("shortened") is not False:
            raise CheckFailure(f"{label}: demo {name} was shortened")
        if len(fit["lines"]) * fit["lineHeight"] > fit["box"]["height"] + 0.5:
            raise CheckFailure(f"{label}: {name} text exceeds its height")
        if fit["maxLineWidth"] > fit["box"]["width"] + 0.5:
            raise CheckFailure(f"{label}: {name} text exceeds its width")
    check_box(layout.get("logoBox"), "logo")
    if layout.get("qrBox"):
        qr = layout["qrBox"]
        check_box(qr, "QR code")
        boxes = {name: fit["box"] for name, fit in fits.items()}
        boxes["logo"] = layout["logoBox"]
        for name, box in boxes.items():
            if (min(qr["x"] + qr["width"], box["x"] + box["width"]) > max(qr["x"], box["x"])
                    and min(qr["y"] + qr["height"], box["y"] + box["height"]) > max(qr["y"], box["y"])):
                raise CheckFailure(f"{label}: QR code overlaps {name}")


def _extract_report(dumped_dom: str, label: str) -> dict[str, Any]:
    matches = REPORT_RE.findall(dumped_dom)
    if not matches:
        raise CheckFailure(
            _with_runtime_errors(
                f"{label}: no #factory-check-report marker was found. "
                "Check mode did not initialize.",
                dumped_dom,
            )
        )
    raw = html.unescape(matches[-1]).strip()
    try:
        report = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CheckFailure(f"{label}: factory report is not valid JSON: {exc}") from exc
    if not isinstance(report, dict):
        raise CheckFailure(f"{label}: factory report must be a JSON object")
    for key in ("overflow", "missing"):
        if key not in report or not isinstance(report[key], list):
            raise CheckFailure(f"{label}: factory report needs a `{key}` array")
    if report.get("ready") is not True:
        raise CheckFailure(f"{label}: factory report did not confirm ready=true")
    if report["overflow"]:
        raise CheckFailure(
            f"{label}: elements overflow their boxes:\n"
            + json.dumps(report["overflow"], indent=2, ensure_ascii=False)
        )
    if report["missing"]:
        raise CheckFailure(
            f"{label}: required flyer content is missing:\n"
            + json.dumps(report["missing"], indent=2, ensure_ascii=False)
        )
    return report


def _diagnostics(report: dict[str, Any], label: str) -> dict[str, Any]:
    diagnostics = report.get("diagnostics")
    if not isinstance(diagnostics, dict):
        raise CheckFailure(
            f"{label}: factory report needs a diagnostics object so the checker can "
            "independently confirm viewport width, logo, and contact output"
        )
    return diagnostics


def _number(diagnostics: dict[str, Any], key: str, label: str) -> float:
    value = diagnostics.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CheckFailure(f"{label}: diagnostics.{key} must be a number")
    return float(value)


def _check_report_details(
    report: dict[str, Any], demo: str, label: str, expected_width: int
) -> None:
    diagnostics = _diagnostics(report, label)
    if diagnostics.get("layout") != ("event" if demo == "event-qr" else PRESETS.get(demo, {}).get("values", {}).get("layout", demo)):
        raise CheckFailure(
            f"{label}: expected layout {demo!r}, got {diagnostics.get('layout')!r}"
        )
    if demo in PRESETS and diagnostics.get("preset") != demo:
        raise CheckFailure(f"{label}: requested preset did not load")
    if diagnostics.get("logoPresent") is not True:
        raise CheckFailure(f"{label}: rendered flyer logo was not found")
    if diagnostics.get("contactPresent") is not True:
        raise CheckFailure(f"{label}: rendered flyer contact line was not found")

    if demo == "event-qr" and diagnostics.get("qrPresent") is not True:
        raise CheckFailure(f"{label}: QR demo did not render its QR code")

    viewport_width = _number(diagnostics, "viewportWidth", label)
    client_width = _number(diagnostics, "documentClientWidth", label)
    scroll_width = _number(diagnostics, "documentScrollWidth", label)
    # Headless Chrome on Windows reports a viewport a few px narrower than --window-size
    # (window frame/scrollbar); the layout checks below are what matter.
    if not (expected_width - 32) <= viewport_width <= expected_width + 1:
        raise CheckFailure(
            f"{label}: Chrome viewport is {viewport_width:g}px; expected about {expected_width}px"
        )
    if scroll_width > client_width + 1:
        raise CheckFailure(
            f"{label}: page scrolls horizontally "
            f"({scroll_width:g}px content in {client_width:g}px viewport)"
        )


def _check_screenshot(path: Path, expected_size: tuple[int, int], label: str) -> None:
    if not path.is_file() or path.stat().st_size < 1000:
        raise CheckFailure(f"{label}: Chrome did not create a usable screenshot")
    try:
        with Image.open(path) as image:
            image.load()
            if image.size != expected_size:
                raise CheckFailure(
                    f"{label}: screenshot is {image.size[0]}x{image.size[1]}; "
                    f"expected {expected_size[0]}x{expected_size[1]}"
                )
            stats = ImageStat.Stat(image.convert("L"))
            extrema = stats.extrema[0]
            deviation = stats.stddev[0]
    except CheckFailure:
        raise
    except Exception as exc:
        raise CheckFailure(f"{label}: screenshot cannot be read: {exc}") from exc
    if extrema[1] - extrema[0] < 20 or deviation < 3:
        raise CheckFailure(
            f"{label}: screenshot appears blank "
            f"(tone range {extrema[0]}-{extrema[1]}, deviation {deviation:.2f})"
        )


def _check_pdf(path: Path, demo: str) -> None:
    label = f"{demo} PDF"
    if not path.is_file() or path.stat().st_size < 1000:
        raise CheckFailure(f"{label}: Chrome did not create a usable PDF")
    try:
        reader = PdfReader(path)
        if len(reader.pages) != 1:
            raise CheckFailure(f"{label}: expected 1 page, found {len(reader.pages)}")
        page = reader.pages[0]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        if abs(width - LETTER_POINTS[0]) > 0.75 or abs(height - LETTER_POINTS[1]) > 0.75:
            raise CheckFailure(
                f"{label}: expected US Letter 612x792 pt, got {width:.2f}x{height:.2f} pt"
            )
        text = page.extract_text() or ""
        if not CONTACT_RE.search(text):
            raise CheckFailure(
                f"{label}: no email, phone, social handle, or web address was found "
                "in the printed flyer text"
            )
        try:
            image_count = len(page.images)
        except Exception as exc:
            raise CheckFailure(f"{label}: could not inspect embedded images: {exc}") from exc
        if image_count < 1:
            raise CheckFailure(f"{label}: no embedded logo image was found")
    except CheckFailure:
        raise
    except Exception as exc:
        raise CheckFailure(f"{label}: PDF cannot be read: {exc}") from exc


def _archive_kept_artifacts() -> None:
    """Move prior named evidence aside before a new --keep run replaces it."""
    if not KEEP_DIR.exists():
        return
    old = [
        path
        for path in KEEP_DIR.iterdir()
        if path.is_file() and path.name in OWNED_ARTIFACTS
    ]
    if not old:
        return
    stamp = datetime.now().strftime("%H%M%S-%f")
    archive = ROOT / "_archive" / "2026-10-11" / "tools" / "html" / "factory" / stamp
    archive.mkdir(parents=True, exist_ok=True)
    for path in old:
        shutil.move(str(path), str(archive / path.name))
    print(f"Archived {len(old)} prior kept artifact(s) to {archive.relative_to(ROOT)}")


def _render_dom_and_png(
    chrome: Path,
    profile: Path,
    output_dir: Path,
    demo: str,
    size: tuple[int, int],
    suffix: str,
) -> dict[str, Any]:
    label = f"{demo} {suffix}"
    screenshot = output_dir / f"{demo}-{suffix}.png"
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise CheckFailure(
            f"{label}: deterministic report polling requires the installed Python playwright package"
        ) from exc

    dumped_dom = ""
    runtime_errors: list[str] = []
    external: list[str] = []
    try:
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(
                str(profile),
                executable_path=str(chrome),
                headless=True,
                viewport={"width": size[0], "height": size[1]},
                device_scale_factor=1,
                args=[
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-breakpad",
                    "--disable-crash-reporter",
                    "--hide-scrollbars",
                    "--disable-background-networking",
                    "--disable-component-update",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--no-first-run",
                    "--allow-file-access-from-files",
                    "--force-device-scale-factor=1",
                    "--run-all-compositor-stages-before-draw",
                    f"--window-size={size[0]},{size[1]}",
                ],
            )
            try:
                def route_request(route: Any) -> None:
                    if route.request.url.startswith(("http:", "https:")):
                        external.append(route.request.url)
                        route.abort()
                    else:
                        route.continue_()

                context.route("**/*", route_request)
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(_page_url(demo), wait_until="load")
                try:
                    page.wait_for_function(
                        """() => {
                          const check = document.getElementById('factory-check-report');
                          if (!check) return false;
                          try { return JSON.parse(check.textContent).ready === true; }
                          catch (_) { return false; }
                        }""",
                        timeout=15000,
                        polling=50,
                    )
                except PlaywrightTimeoutError as exc:
                    runtime_errors = page.evaluate("() => [...(window.factoryRuntimeErrors || [])]")
                    raise CheckFailure(
                        f"{label}: timed out polling deterministic report nodes\n"
                        f"Page runtimeErrors:\n{json.dumps(runtime_errors, indent=2, ensure_ascii=False)}"
                    ) from exc
                page.screenshot(path=str(screenshot))
                dumped_dom = page.content()
                if suffix == "desktop":
                    _check_social(page, output_dir, demo)
            finally:
                context.close()
    except CheckFailure:
        raise
    except Exception as exc:
        raise CheckFailure(f"{label}: browser report polling failed: {exc}") from exc

    if external:
        raise CheckFailure(f"{label}: unexpected network requests: {external}")
    report = _extract_report(dumped_dom, label)
    _check_report_details(report, demo, label, size[0])
    _check_screenshot(screenshot, size, label)
    return report


def _print_from_button(page: Any, output: Path, demo: str) -> None:
    # Headless Chrome has no print dialog. Intercept only that final browser
    # boundary; validation and print preparation must run through the real UI.
    page.evaluate("window.__printRequested = false; window.print = () => { window.__printRequested = true; }")
    page.locator('#invoice-print' if demo == 'invoice' else '#print-button').click()
    page.wait_for_function("window.__printRequested === true", timeout=15000)
    page.pdf(path=str(output), prefer_css_page_size=True, print_background=True)
    page.evaluate("window.dispatchEvent(new Event('afterprint'))")
    _check_pdf(output, demo)


def _render_pdf(chrome: Path, profile: Path, output_dir: Path, demo: str) -> None:
    from playwright.sync_api import sync_playwright
    external = []
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            str(profile), executable_path=str(chrome), headless=True,
            viewport={"width": DESKTOP_SIZE[0], "height": DESKTOP_SIZE[1]},
            args=['--no-sandbox', '--disable-gpu', '--disable-background-networking',
                  '--disable-component-update', '--allow-file-access-from-files'])
        try:
            def route_request(route: Any) -> None:
                if route.request.url.startswith(('http:', 'https:')):
                    external.append(route.request.url)
                    route.abort()
                else:
                    route.continue_()
            context.route('**/*', route_request)
            page = context.pages[0]
            page.goto(_page_url(demo))
            page.evaluate('() => window.factoryReady')
            _print_from_button(page, output_dir / f"{demo}-letter.pdf", demo)
            if external:
                raise CheckFailure(f"{demo} PDF: unexpected network requests: {external}")
        finally:
            context.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep PNG and PDF evidence under tools/html/factory/",
    )
    parser.add_argument(
        "--social",
        action="store_true",
        help="check only desktop and the three social PNG sizes (also included in the default run)",
    )
    parser.add_argument(
        "--chrome",
        type=Path,
        default=DEFAULT_CHROME,
        help=f"Chrome executable (default: {DEFAULT_CHROME})",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    chrome = args.chrome.expanduser().resolve()
    if not chrome.is_file():
        raise CheckFailure(f"Chrome executable not found: {chrome}")
    if not FACTORY_PAGE.is_file():
        raise CheckFailure(f"Flyer Factory page not found: {FACTORY_PAGE}")
    missing_dependencies = []
    if PIL_IMPORT_ERROR is not None:
        missing_dependencies.append("Pillow")
    if PYPDF_IMPORT_ERROR is not None:
        missing_dependencies.append("pypdf")
    if missing_dependencies:
        names = " and ".join(missing_dependencies)
        raise CheckFailure(
            f"Missing Python dependency: {names}. Install it for this Python "
            f"environment, then rerun: python -m pip install {' '.join(missing_dependencies)}"
        )

    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

    if args.keep:
        _archive_kept_artifacts()
        KEEP_DIR.mkdir(parents=True, exist_ok=True)
        output_context: Any = _ExistingDirectory(KEEP_DIR)
    else:
        output_context = _ResilientTemporaryDirectory(
            prefix="run-", dir=SCRATCH_DIR, ignore_cleanup_errors=True
        )

    with output_context as directory:
        output_dir = Path(directory)
        with _ResilientTemporaryDirectory(
            prefix="profile-", dir=SCRATCH_DIR, ignore_cleanup_errors=True
        ) as profile_name:
            profile = Path(profile_name)
            for demo in DEMOS:
                _render_dom_and_png(chrome, profile, output_dir, demo, DESKTOP_SIZE, "desktop")
                print(f"PASS {demo}: desktop report and square 1080x1080, story 1080x1920, Facebook 1920x1005 PNGs")
                if not args.social:
                    _render_pdf(chrome, profile, output_dir, demo)
                    print(f"PASS {demo}: nonblank PNG, 1-page Letter PDF")

            if not args.social:
                from check_factory_browser import check_browser
                check_browser(chrome, output_dir)
                from check_factory_orders import check_orders
                check_orders(chrome, output_dir)
                from check_factory_ai import check_ai
                check_ai(chrome, output_dir)
                _render_pdf(chrome, profile, output_dir, "invoice")
                print("PASS invoice: 1-page Letter PDF")

        if args.keep:
            print(f"Evidence kept in {output_dir}")
    checks = "desktop and social" if args.social else "desktop, print, mobile, and social"
    subjects = "all layouts and presets" if args.social else "all layouts, presets, order and invoice"
    print(f"PASS Flyer Factory: {subjects} passed {checks} checks")
    return 0


class _ExistingDirectory:
    """Context-manager adapter with the same interface as TemporaryDirectory."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> str:
        return str(self.path)

    def __exit__(self, *_: object) -> None:
        return None


class _PassCounter:
    """Count "PASS ..." lines so the run ends with a pytest-style summary the
    AI Council's receipt parser can read (it ignores bespoke PASS output)."""

    def __init__(self, stream) -> None:
        self.stream = stream
        self.passed = 0
        self._pending = ""

    def write(self, text: str) -> int:
        self._pending += text
        *lines, self._pending = self._pending.split(chr(10))
        self.passed += sum(1 for line in lines if line.startswith("PASS "))
        return self.stream.write(text)

    def flush(self) -> None:
        self.stream.flush()

    def __getattr__(self, name: str):
        return getattr(self.stream, name)


if __name__ == "__main__":
    import time as _time
    _started = _time.monotonic()
    _counter = _PassCounter(sys.stdout)
    sys.stdout = _counter
    try:
        _code = main()
    except CheckFailure as exc:
        sys.stdout = _counter.stream
        print(f"FAIL Flyer Factory: {exc}", file=sys.stderr)
        print(f"===== 1 failed, {_counter.passed} passed in {_time.monotonic() - _started:.1f}s =====")
        raise SystemExit(1)
    sys.stdout = _counter.stream
    if _code == 0:
        print(f"===== {_counter.passed} passed in {_time.monotonic() - _started:.1f}s =====")
    raise SystemExit(_code)
