#!/usr/bin/env python3
"""Acceptance checks for the browser-only CultureShyft Flyer Factory.

The checker deliberately uses the same Chrome command-line paths a person uses:
screen rendering and printing.  The page publishes the result of calling
``window.factoryReport()`` in ``script#factory-check-report`` when ``check=1``
is present.  Reading that marker from ``--dump-dom`` lets this script verify the
post-layout browser state without a web server or a browser automation package.

Run from anywhere::

    python tools/check_factory.py
    python tools/check_factory.py --keep

``--keep`` preserves the generated PNG and PDF evidence in
``tools/html/factory``.  Otherwise all artifacts live in a temporary directory.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
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
DEMOS = ("poster", "event", "announcement")
DESKTOP_SIZE = (1440, 1200)
MOBILE_SIZE = (500, 1200)  # headless Chrome on Windows will not go narrower than 500px
LETTER_POINTS = (612.0, 792.0)
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
)


class CheckFailure(RuntimeError):
    """An acceptance condition failed with a user-actionable explanation."""


class _ResilientTemporaryDirectory(tempfile.TemporaryDirectory[str]):
    """Keep a primary check failure visible if Windows denies temp cleanup."""

    def __exit__(self, exc: object, value: object, traceback: object) -> None:
        try:
            super().__exit__(exc, value, traceback)
        except OSError as cleanup_error:
            print(
                f"WARNING: temporary evidence could not be cleaned up: {cleanup_error}",
                file=sys.stderr,
            )


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
        "--virtual-time-budget=8000",
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


def _page_url(demo: str) -> str:
    return f"{FACTORY_PAGE.as_uri()}?{urlencode({'demo': demo, 'check': '1'})}"


def _extract_report(dumped_dom: str, label: str) -> dict[str, Any]:
    matches = REPORT_RE.findall(dumped_dom)
    if not matches:
        raise CheckFailure(
            f"{label}: no #factory-check-report marker was found. "
            "The page may not have finished window.factoryReady or check mode may be broken."
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
    if diagnostics.get("layout") != demo:
        raise CheckFailure(
            f"{label}: expected layout {demo!r}, got {diagnostics.get('layout')!r}"
        )
    if diagnostics.get("logoPresent") is not True:
        raise CheckFailure(f"{label}: rendered flyer logo was not found")
    if diagnostics.get("contactPresent") is not True:
        raise CheckFailure(f"{label}: rendered flyer contact line was not found")

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
    archive = ROOT / "_archive" / date.today().isoformat() / "tools" / "html" / "factory" / stamp
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
    result = _run_chrome(
        chrome,
        profile,
        [
            f"--window-size={size[0]},{size[1]}",
            "--dump-dom",
            f"--screenshot={screenshot}",
            _page_url(demo),
        ],
        label,
    )
    report = _extract_report(result.stdout, label)
    _check_report_details(report, demo, label, size[0])
    _check_screenshot(screenshot, size, label)
    return report


def _render_dom_and_png_with_retry(chrome, profile, output_dir, demo, size, suffix, attempts: int = 3):
    """Headless Chrome occasionally dumps the DOM before fonts settle (ready=false); retry that one race."""
    for attempt in range(1, attempts + 1):
        try:
            return _render_dom_and_png(chrome, profile, output_dir, demo, size, suffix)
        except CheckFailure as exc:
            if "ready=true" not in str(exc) or attempt == attempts:
                raise
            print(f"RETRY {demo} {suffix}: report not ready on attempt {attempt}; rendering again")


def _render_pdf(chrome: Path, profile: Path, output_dir: Path, demo: str) -> None:
    output = output_dir / f"{demo}-letter.pdf"
    _run_chrome(
        chrome,
        profile,
        [
            "--no-pdf-header-footer",
            f"--print-to-pdf={output}",
            _page_url(demo),
        ],
        f"{demo} PDF",
    )
    _check_pdf(output, demo)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep PNG and PDF evidence under tools/html/factory/",
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
                _render_dom_and_png_with_retry(
                    chrome, profile, output_dir, demo, DESKTOP_SIZE, "desktop"
                )
                _render_pdf(chrome, profile, output_dir, demo)
                print(f"PASS {demo}: desktop report, nonblank PNG, 1-page Letter PDF")

            for demo in DEMOS:
                _render_dom_and_png_with_retry(
                    chrome, profile, output_dir, demo, MOBILE_SIZE, "mobile"
                )
                print(f"PASS {demo}: 500px mobile (narrowest headless Chrome allows), no horizontal scroll")

        if args.keep:
            print(f"Evidence kept in {output_dir}")
    print("PASS Flyer Factory: all 3 layouts passed desktop, print, and mobile checks")
    return 0


class _ExistingDirectory:
    """Context-manager adapter with the same interface as TemporaryDirectory."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def __enter__(self) -> str:
        return str(self.path)

    def __exit__(self, *_: object) -> None:
        return None


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckFailure as exc:
        print(f"FAIL Flyer Factory: {exc}", file=sys.stderr)
        raise SystemExit(1)
