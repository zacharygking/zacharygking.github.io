#!/usr/bin/env python3
"""Static checks for the site, with no dependencies (Python 3.9+).

    python3 tests/check_site.py                   # reads resume.pdf with pdftotext if it's installed
    python3 tests/check_site.py --require-pdf     # fail if resume.pdf can't be read (CI)
    python3 tests/check_site.py --pdf-text FILE   # use text already extracted from resume.pdf
    python3 tests/check_site.py --root DIR        # check another copy of the site

Checks that tags are balanced and ids unique; that every in-page link, illustration reference and
local file resolves; that the head has the mobile and color-scheme tags; that every color token has a
dark-mode and a print value; that the stats row matches source/og.html; that no phone number appears;
and that the page and resume.pdf list the same contact links. Exits 1 if any check fails.
"""

import argparse
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

SITE_URL = "https://zacharygking.github.io/"
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

# Any common phone-number format. It's generic on purpose, so no real number goes in this public repo,
# and matches are reported with their digits masked, so none lands in a public CI log either.
PHONE = re.compile(r"(?<![\d.,])(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4}(?![\d.,])")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
WEB_ADDRESS = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:com|io|org|net|dev|me|ai)(?:/[\w.-]+)+", re.I)
TOKEN = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")
COLOR_VALUE = re.compile(r"^(#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(|oklch\(|color-mix\()", re.I)


class Page(HTMLParser):
    """Reads one HTML file: ids, link-like attributes, meta tags, visible text and unbalanced tags."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.ids = []
        self.links = []  # (tag, attribute, value) for href, src and content
        self.attr_values = []
        self.metas = []
        self.text = []
        self.problems = []
        self._open = []  # (tag, line)
        self._raw_text = 0  # depth inside <style> or <script>, whose text isn't visible

    def handle_starttag(self, tag, attrs):
        self._read_attrs(tag, attrs)
        if tag not in VOID_TAGS:
            self._open.append((tag, self.getpos()[0]))
            if tag in ("style", "script"):
                self._raw_text += 1

    def handle_startendtag(self, tag, attrs):
        self._read_attrs(tag, attrs)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        if all(open_tag != tag for open_tag, _ in self._open):
            self.problems.append(f"line {self.getpos()[0]}: </{tag}> has no open <{tag}>")
            return
        while self._open:
            open_tag, line = self._open.pop()
            if open_tag in ("style", "script"):
                self._raw_text -= 1
            if open_tag == tag:
                break
            self.problems.append(f"line {line}: <{open_tag}> is never closed")

    def handle_data(self, data):
        if not self._raw_text:
            self.text.append(data)

    def close(self):
        super().close()
        self.problems += [f"line {line}: <{tag}> is never closed" for tag, line in self._open]

    def _read_attrs(self, tag, attrs):
        attrs = {name: value or "" for name, value in attrs}
        if tag == "html":
            self.lang = attrs.get("lang")
        if tag == "meta":
            self.metas.append(attrs)
        for name, value in attrs.items():
            self.attr_values.append(value)
            if name == "id":
                self.ids.append(value)
            elif name in ("href", "src", "content"):
                self.links.append((tag, name, value))


def parse(path):
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    page.close()
    return page


def without_comments(html):
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


def local_file(value, attribute):
    """The repo path an attribute value points to, or None if it points somewhere else."""
    if value.startswith(SITE_URL):
        path = value[len(SITE_URL):]
    elif attribute == "content" or value.startswith(("#", "//")) or re.match(r"^[a-z][a-z0-9+.-]*:", value, re.I):
        return None
    else:
        path = value
    path = path.split("#")[0].split("?")[0]
    return path + "index.html" if path == "" or path.endswith("/") else path


def check_structure(root, page):
    problems = list(page.problems)
    ids = set(page.ids)
    problems += sorted({f'id "{i}" is used more than once' for i in page.ids if page.ids.count(i) > 1})
    for tag, attribute, value in page.links:
        # A bare # or #top scrolls to the top of the page without a matching id.
        target = value[1:]
        if attribute == "href" and value.startswith("#") and target.lower() not in ("", "top") and target not in ids:
            problems.append(f'<{tag} href="{value}"> points to no id on the page')
        path = local_file(value, attribute)
        if path and not (root / path).is_file():
            problems.append(f'<{tag} {attribute}="{value}"> points to a missing file')
    refs = {ref for value in page.attr_values for ref in re.findall(r"url\(#([^)]+)\)", value)}
    problems += [f"url(#{ref}) points to no id on the page" for ref in sorted(refs - ids)]
    return problems


def check_head(page):
    def named(name):
        return [meta for meta in page.metas if meta.get("name") == name]

    problems = []
    if not page.lang:
        problems.append("<html> has no lang")
    if not any("width=device-width" in meta.get("content", "") for meta in named("viewport")):
        problems.append("no viewport meta with width=device-width, so phones would show a zoomed-out desktop page")
    if not any({"light", "dark"} <= set(meta.get("content", "").split()) for meta in named("color-scheme")):
        problems.append('no color-scheme meta with "light dark"')
    for scheme in ("light", "dark"):
        if not any(f"prefers-color-scheme: {scheme}" in meta.get("media", "") for meta in named("theme-color")):
            problems.append(f"no theme-color meta for {scheme} mode")
    return problems


def check_theme(root):
    css = (root / "styles.css").read_text(encoding="utf-8")
    light = re.search(r"^:root\s*\{(.*?)\}", css, re.M | re.S)
    dark = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*:root\s*\{(.*?)\}", css, re.S)
    printed = re.search(r"@media\s+print\s*\{\s*:root\s*\{(.*?)\}", css, re.S)
    if not (light and dark and printed):
        return ["styles.css: couldn't find the :root blocks for light, dark mode and print"]

    light, dark, printed = (dict(TOKEN.findall(block.group(1))) for block in (light, dark, printed))
    colors = {name for name, value in light.items() if COLOR_VALUE.match(value.strip())}
    problems = []
    for label, tokens in (("dark-mode", dark), ("print", printed)):
        problems += [f"--{name} has no {label} value" for name in sorted(colors - set(tokens))]
        problems += [f"--{name} has a {label} value but isn't in :root" for name in sorted(set(tokens) - set(light))]
    used = set(re.findall(r"var\(--([\w-]+)", css))
    problems += [f"var(--{name}) is used but never defined" for name in sorted(used - set(light))]
    return problems


def stats_row(html):
    block = re.search(r'<dl class="stats">(.*?)</dl>', html, re.S)
    if not block:
        return None
    pairs = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", block.group(1), re.S)
    return [(" ".join(label.split()), value.strip()) for label, value in pairs]


def check_stats(root, html):
    page = stats_row(html)
    preview = stats_row(without_comments((root / "source" / "og.html").read_text(encoding="utf-8")))
    if not page:
        return ['index.html has no <dl class="stats"> row']
    if page != preview:
        return [f"index.html has {page}", f"source/og.html has {preview}; update it and re-render og.png"]
    return []


def masked(text):
    return re.sub(r"\d", "#", text)


def check_phone_numbers(root, pdf_text):
    problems = []
    files = sorted({*root.glob("*.html"), *root.glob("source/*.html"), *root.glob("*.md"), *root.glob("*.txt")})
    for path in files:
        name = path.relative_to(root)
        if path.suffix == ".html":
            page = parse(path)
            text = " ".join(page.text + [value for _, _, value in page.links])
            if any(value.lower().startswith("tel:") for _, _, value in page.links):
                problems.append(f"{name} has a tel: link")
        else:
            text = path.read_text(encoding="utf-8")
        problems += [f"{name} has a phone number: {masked(hit)}" for hit in PHONE.findall(text)]
    if pdf_text is not None:
        problems += [f"resume.pdf has a phone number: {masked(hit)}" for hit in PHONE.findall(pdf_text)]
    return problems


def contact_links(html):
    block = re.search(r'<ul class="contact"[^>]*>(.*?)</ul>', html, re.S)
    if not block:
        return None
    links = set()
    for href in re.findall(r'href="([^"]+)"', block.group(1)):
        if href.startswith("mailto:"):
            links.add(href[len("mailto:"):].lower())
        else:
            links.add(re.sub(r"^https?://(www\.)?", "", href).rstrip("/").lower())
    return links


def resume_links(text):
    emails = {email.lower() for email in EMAIL.findall(text)}
    addresses = {address.rstrip("/.").lower() for address in WEB_ADDRESS.findall(EMAIL.sub(" ", text))}
    return emails | addresses


def check_contact(html, pdf_text):
    page = contact_links(html)
    if page is None:
        return ['index.html has no <ul class="contact">']
    resume = resume_links(pdf_text)
    return (
        [f"{link} is on the page but not in resume.pdf" for link in sorted(page - resume)]
        + [f"{link} is in resume.pdf but not on the page" for link in sorted(resume - page)]
    )


def read_resume(root, args):
    """Returns resume.pdf's text and None, or None and the reason it couldn't be read."""
    if args.pdf_text:
        return Path(args.pdf_text).read_text(encoding="utf-8"), None
    if not shutil.which("pdftotext"):
        return None, "pdftotext isn't installed; install poppler or pass --pdf-text"
    run = subprocess.run(["pdftotext", "-layout", str(root / "resume.pdf"), "-"], capture_output=True, text=True)
    if run.returncode != 0:
        return None, f"pdftotext failed: {run.stderr.strip()}"
    return run.stdout, None


def main():
    parser = argparse.ArgumentParser(description="Static checks for the site.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent, help="site folder to check")
    parser.add_argument("--pdf-text", help="text already extracted from resume.pdf")
    parser.add_argument("--require-pdf", action="store_true", help="fail if resume.pdf can't be read")
    args = parser.parse_args()

    root = args.root.resolve()
    page = parse(root / "index.html")
    html = without_comments((root / "index.html").read_text(encoding="utf-8"))
    pdf_text, unreadable = read_resume(root, args)

    checks = [
        ("tags, ids, in-page links and local files", check_structure(root, page)),
        ("mobile and color-scheme head tags", check_head(page)),
        ("every color token has dark-mode and print values", check_theme(root)),
        ("stats row matches source/og.html", check_stats(root, html)),
        ("no phone numbers", check_phone_numbers(root, pdf_text)),
    ]
    if pdf_text is not None:
        checks.append(("contact links match resume.pdf", check_contact(html, pdf_text)))
    elif args.require_pdf:
        checks.append(("resume.pdf is readable", [unreadable]))

    failures = 0
    for name, problems in checks:
        print(f"{'FAIL' if problems else 'ok  '}  {name}")
        for problem in problems:
            print(f"      - {problem}")
        failures += bool(problems)
    if pdf_text is None and not args.require_pdf:
        print(f"skip  resume.pdf phone and contact checks: {unreadable}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
