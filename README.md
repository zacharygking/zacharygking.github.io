# zacharygking.github.io

[![Checks](https://github.com/zacharygking/zacharygking.github.io/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/zacharygking/zacharygking.github.io/actions/workflows/checks.yml)

My personal site: one static page in plain HTML and CSS. No build step and no dependencies. The
only JavaScript is the GoatCounter analytics script (see [Analytics](#analytics)).

**Everything in this repo is public, including this README and the full commit history.**
Don't commit private notes.

## Files

- `index.html`: all page content, in page order.
- `styles.css`: layout and colors. Color tokens are at the top, with the dark-mode overrides
  right below them.
- `resume.pdf`: the resume linked from the page. It's the site build, with no phone number.
- `favicon.svg`, `favicon-32.png`, `apple-touch-icon.png`: the ZK icon. The PNGs are rendered
  from `source/icon.html`.
- `og.png`: the 1200×630 link-preview image, rendered from `source/og.html`. Both source pages
  start with the headless Chrome command that renders them.
- `favicon.ico`: the 32px icon wrapped as an ICO, for tools that only ask for `/favicon.ico`.
- `robots.txt`: allows all crawlers.
- `.nojekyll`: tells GitHub Pages to serve the files as they are.
- `tests/` and `.github/workflows/checks.yml`: the checks described below.

## Editing

- **Case studies** are cards in `#work`. To add one, copy an `<article class="case">` block:
  an `id`, a 400×160 inline SVG illustration, one chip, a kicker, a heading, and 2–4
  sentences. Illustration colors come from classes in `styles.css`, and the shared arrowhead
  and dot patterns live in the hidden `<svg class="defs">` at the top of the page.
- **Stats** under the name are a `<dl class="stats">`. Keep each label specific about what
  its number counts. `source/og.html` repeats them, so update it and re-render `og.png` too.
  The static checks fail if the two differ.
- **Experience:** each work item is a `.work-name` and a `.detail`. Work that has a card links to
  it by `id` (`<span class="work-name"><a href="#tone">…</a></span>`).
- **Projects:** a commented-out `#projects` section sits right after `#work`. Uncomment it
  when there's something public to show.
- **Resume:** overwrite `resume.pdf` with the site build of the resume (no phone number),
  keeping the same file name.
- **Footer year:** update it in `index.html`.

To preview, open `index.html` in a browser.

## Analytics

[GoatCounter](https://www.goatcounter.com) counts page views without cookies. The dashboard is at
https://zacharygking.goatcounter.com.

- The script tag at the end of `index.html` loads a versioned `count.vN.js`, pinned by its SRI
  hash. To upgrade, change the file name and the `integrity` value together. The render checks fail
  if they don't match. To get the hash:
  `curl -s https://gc.zgo.at/count.vN.js | openssl dgst -sha384 -binary | openssl base64 -A`
- Links with a `data-goatcounter-click` name also count clicks, as events: the Resume button and the
  contact links.
- Previews from `file://` or localhost aren't counted. To stop counting your own visits in one
  browser, open https://zacharygking.github.io/#toggle-goatcounter; open it again to undo.

## Checks

GitHub Actions runs two jobs on every push:

- **Static checks** (`tests/check_site.py`, no dependencies):
  - tags are balanced and ids are unique
  - in-page links, illustration references and local files all resolve
  - the head has the mobile and color-scheme tags
  - every script is a third-party file over https, pinned by an integrity hash and loaded `async`
    or `defer`
  - every color token has a dark-mode and a print value
  - the stats match `source/og.html`
  - no phone number appears in the page or the resume
  - the page and `resume.pdf` list the same contact links
- **Render checks** (`tests/test_render.py`): Chromium and WebKit on macOS, at phone, tablet and
  desktop widths, in light and dark mode.
  - The page must not scroll sideways.
  - Tap targets on phones must be at least 44px tall.
  - axe-core's WCAG 2.2 A and AA rules, including color contrast, must pass.
  - GoatCounter's script must load, match its integrity hash and bind its click events. Its hits
    are blocked, and the other checks block the script too, so none of them need the network.
  - Each run uploads screenshots.

Pages publishes `main` whether or not the checks pass, so run them before pushing:

```sh
python3 tests/check_site.py          # reads resume.pdf with pdftotext; without it, pass --pdf-text FILE
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r tests/requirements.txt
.venv/bin/python -m playwright install chromium webkit
.venv/bin/python -m pytest tests -q  # screenshots go to tests/screenshots/
```

## Deploying

GitHub Pages publishes the `main` branch automatically:

```sh
git add -A
git commit -m "Describe the change"
git push
```

Changes are usually live within a couple of minutes.
