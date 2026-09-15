"""Render checks: the page at phone, tablet and desktop widths, in light and dark mode.

    uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r tests/requirements.txt
    .venv/bin/python -m playwright install chromium webkit
    .venv/bin/python -m pytest tests -q

ENGINES picks the browsers (default "chromium,webkit"). PW_CHROMIUM_CHANNEL=chrome runs the installed
Google Chrome instead of a downloaded Chromium. Screenshots are saved to tests/screenshots/.
"""

import os
import re
from pathlib import Path

import pytest
from axe_playwright_python.base import AXE_SCRIPT
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGE_URL = (ROOT / "index.html").as_uri()
SCREENSHOTS = ROOT / "tests" / "screenshots"

ENGINES = [name.strip() for name in os.environ.get("ENGINES", "chromium,webkit").split(",") if name.strip()]
SCHEMES = ["light", "dark"]
PHONE_WIDTHS = [320, 360, 390, 430]
WIDTHS = PHONE_WIDTHS + [768, 1280]
SCREENSHOT_WIDTHS = {390, 768, 1280}
PHONE_LAYOUT_MAX = 576  # 36rem: below this, styles.css switches to the phone top bar and 44px tap targets
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]


@pytest.fixture(scope="session")
def pw():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session", params=ENGINES)
def browser(request, pw):
    browser_type = getattr(pw, request.param)
    channel = os.environ.get("PW_CHROMIUM_CHANNEL") if request.param == "chromium" else None
    browser = browser_type.launch(channel=channel) if channel else browser_type.launch()
    yield browser
    browser.close()


@pytest.fixture
def open_page(browser):
    contexts = []

    def open_at(width, scheme="light"):
        phone = width <= PHONE_LAYOUT_MAX
        context = browser.new_context(
            viewport={"width": width, "height": 800},
            device_scale_factor=2,
            is_mobile=phone,
            has_touch=phone,
            color_scheme=scheme,
            # The cards' scroll-driven rise-in would otherwise leave some half-faded in screenshots and contrast checks
            reduced_motion="reduce",
        )
        contexts.append(context)
        page = context.new_page()
        page.goto(PAGE_URL)
        return page

    yield open_at
    for context in contexts:
        context.close()


def luminance(css_color):
    """Relative luminance of a computed color like rgb(12, 13, 16) or color(srgb 0.05 0.05 0.06)."""
    channels = [float(value) for value in re.findall(r"[\d.]+", css_color)[:3]]
    if css_color.startswith("color("):
        channels = [value * 255 for value in channels]
    linear = [(c / 255 / 12.92) if c / 255 <= 0.04045 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("width", WIDTHS)
def test_no_sideways_scrolling(browser, open_page, width, scheme):
    page = open_page(width, scheme)
    layout = page.evaluate(
        """() => {
            const limit = document.documentElement.clientWidth;
            const wide = [...document.querySelectorAll('body *')]
                .filter(el => !el.closest('svg') && el.getBoundingClientRect().right > limit + 0.5)
                .map(el => el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).trim().replace(/\\s+/g, '.') : ''));
            return {scrollWidth: document.documentElement.scrollWidth, limit, wide: wide.slice(0, 8)};
        }"""
    )
    if width in SCREENSHOT_WIDTHS:
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(SCREENSHOTS / f"{browser.browser_type.name}-{width}-{scheme}.png"), full_page=True)
    assert layout["scrollWidth"] <= layout["limit"], f"the page scrolls sideways at {width}px; too wide: {layout['wide']}"


@pytest.mark.parametrize("width", PHONE_WIDTHS)
def test_phone_tap_targets(open_page, width):
    page = open_page(width)
    small = page.evaluate(
        """() => [...document.querySelectorAll('a[href], button')]
            .filter(el => el.getClientRects().length > 0)
            .map(el => {
                const box = el.getBoundingClientRect();
                return {link: el.textContent.trim() || el.getAttribute('aria-label'), width: Math.round(box.width), height: Math.round(box.height)};
            })
            .filter(target => target.height < 44 || target.width < 24)"""
    )
    assert not small, f"tap targets under 44px tall or 24px wide at {width}px: {small}"


@pytest.mark.parametrize("scheme", SCHEMES)
def test_color_scheme_applies(open_page, scheme):
    page = open_page(1280, scheme)
    background, text = page.evaluate(
        "() => { const style = getComputedStyle(document.body); return [style.backgroundColor, style.color]; }"
    )
    if scheme == "dark":
        assert luminance(background) < luminance(text), f"dark mode didn't apply: background {background}, text {text}"
    else:
        assert luminance(background) > luminance(text), f"light mode didn't apply: background {background}, text {text}"


@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("width", [390, 1280])
def test_accessibility(open_page, width, scheme):
    """axe-core's WCAG 2.2 A and AA rules, including color contrast and target size."""
    page = open_page(width, scheme)
    page.add_script_tag(content=AXE_SCRIPT)
    results = page.evaluate(
        "options => axe.run(document, options)",
        {"runOnly": {"type": "tag", "values": AXE_TAGS}, "resultTypes": ["violations"]},
    )
    problems = []
    for violation in results["violations"]:
        for node in violation["nodes"][:5]:
            detail = (node.get("failureSummary") or "").splitlines()[-1].strip()
            problems.append(f"{violation['id']}: {' '.join(map(str, node['target']))}: {detail}")
    assert not problems, f"{len(problems)} accessibility problems at {width}px in {scheme} mode:\n" + "\n".join(problems)
