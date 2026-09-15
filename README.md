# zacharygking.github.io

My personal site: one static page in plain HTML and CSS. No build step, no JavaScript, no
dependencies.

**Everything in this repo is public, including this README and the full commit history.**
Don't commit private notes.

## Files

- `index.html`: all page content, in page order.
- `styles.css`: layout and colors. Color tokens are at the top, with the dark-mode overrides
  right below them.
- `resume.pdf`: the resume linked from the page.
- `.nojekyll`: tells GitHub Pages to serve the files as they are.

## Editing

- **Case studies** are in `#work`. To add one, copy an `<article class="case">` block: a
  kicker, a heading, one metric, and 2–4 sentences.
- **Projects:** a commented-out `#projects` section sits right after `#work`. Uncomment it
  when there's something public to show.
- **Resume:** overwrite `resume.pdf`, keeping the same file name.
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
