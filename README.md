# Personal site

A static, one-page site in Spanish, English, and French. It has no build step and no dependencies.

## Preview locally

Open `index.html` in a browser, or serve the folder:

```bash
cd ~/Documents/Codes/personal-site
python3 -m http.server 8000
```

Then visit http://localhost:8000.

## Structure

```
index.html                  Home page (CV content, project cards)
projects/deduplication.html Detail page for the deduplication pipeline (private project)
projects/validation.html    Detail page for the agentic validation website (private project)
assets/site.css             Styles (copy of the CSS inlined into each page)
assets/lang.js              Language switcher (copy of the JS inlined into each page)
```

Each page includes its own CSS and JavaScript inline, so it opens by double-clicking the file, with no other files needed. The pages do not load `assets/`. If you change the styles or the switcher, edit the `<style>` and `<script>` blocks in each HTML file, and keep `assets/` in sync if you want to keep it as a reference.

## Edit the content

Each page keeps its text in a `T` object inside its own `<script>` block, with one entry per language: `es`, `en`, and `fr`. Keep the same keys in each entry. Change the text there rather than in the HTML.

- Home page: `index.html`, `const T`.
- Project pages: `projects/*.html`, `const T`. These pages describe private projects, so keep them at a high level and include only facts you've confirmed. Leave out repository links and code.

The language switcher is in `assets/lang.js`. It stores the visitor's choice in `localStorage`. If storage is unavailable, the page falls back to the browser language, then English.

## Deploy to Hostinger

1. In hPanel, open the File Manager for your domain and go to `public_html`.
2. Upload `index.html` (and any other files you add) to `public_html`.
3. In hPanel, enable the free SSL certificate for the domain.

Keep the files flat, with relative paths only, so the upload works as is.
