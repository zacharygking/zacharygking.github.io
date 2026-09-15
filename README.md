# zacharygking.github.io

My personal site: one static page in plain HTML and CSS. No build step, no dependencies, and
no JavaScript on the page.

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

## Editing

- **Case studies** are cards in `#work`. To add one, copy an `<article class="case">` block:
  an `id`, a 400×160 inline SVG illustration, one chip, a kicker, a heading, and 2–4
  sentences. Illustration colors come from classes in `styles.css`, and the shared arrowhead
  and dot patterns live in the hidden `<svg class="defs">` at the top of the page.
- **Stats** under the name are a `<dl class="stats">`. Keep each label specific about what
  its number counts. `source/og.html` repeats them, so update it and re-render `og.png` too.
- **Experience:** each work item is a `.work-name` and a `.detail`. Work that has a card links to
  it by `id` (`<span class="work-name"><a href="#tone">…</a></span>`).
- **Projects:** a commented-out `#projects` section sits right after `#work`. Uncomment it
  when there's something public to show.
- **Resume:** overwrite `resume.pdf` with the site build of the resume (no phone number),
  keeping the same file name.
- **Footer year:** update it in `index.html`.

To preview, open `index.html` in a browser.

## Deploying

GitHub Pages publishes the `main` branch automatically:

```sh
git add -A
git commit -m "Describe the change"
git push
```

Changes are usually live within a couple of minutes.
