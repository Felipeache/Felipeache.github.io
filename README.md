# Luis Felipe Henao: personal site

A one-page personal site for Luis Felipe Henao, Senior Data Engineer, with two detail pages for private projects. It is written in Spanish, English, and French, and has no build step and no dependencies.

**Live:** https://felipeache.github.io (https://henao.me once the custom domain is active)

## Pages

| File | Contents |
|---|---|
| `index.html` | Home page: hero, about, skills, experience, projects, education, contact |
| `projects/deduplication.html` | Detail page for the deduplication pipeline |
| `projects/validation.html` | Detail page for the agentic validation website |
| `CNAME` | Custom domain used by GitHub Pages (`henao.me`) |

Each page is self-contained. Its styles and scripts are inline, so the page opens by double-clicking the file.

## Run locally

Open `index.html` in a browser, or serve the folder:

```bash
cd ~/Documents/Codes/personal-site
python3 -m http.server 8000
```

Then visit http://localhost:8000.

## Edit the content

Each page keeps its text in a `const T` object inside its `<script>` block, with one entry per language: `en`, `es`, and `fr`. Keep the same keys in every language, and change the text in `T` rather than in the HTML.

## Edit the styles and behaviour

The CSS is in each page's `<style>` block, and the JavaScript is in its `<script>` blocks. A change to a shared style, the theme code, or the language switcher must be made in all three pages.

## Themes and languages

- **Theme:** dark is the default. The button in the header switches to light mode, and the choice is saved in `localStorage` under `site-theme`.
- **Language:** the flags switch between Spanish, English, and French. The first visit uses the browser language, falling back to English. The choice is saved under `site-lang`.

## Private projects

The detail pages describe private work. Keep them at a high level, use only facts you have confirmed, and do not add repository links, internal names, bucket or project IDs, or customer and partner names.

## Deploy

GitHub Pages serves the `main` branch, root folder. To publish a change:

```bash
git add -A
git commit -m "Describe the change"
git push origin main
```

The site rebuilds in about a minute.

## Custom domain

The `CNAME` file holds `henao.me`. The DNS records at the domain registrar are:

- four `A` records for `@` pointing to `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, and `185.199.111.153`
- a `CNAME` record for `www` pointing to `felipeache.github.io`

Keep the existing Zoho mail records (MX, SPF, verification, and DKIM), or email will stop working.

Once the certificate is issued, enable **Enforce HTTPS** in the repository's Settings → Pages.

## Checks before publishing

- No phone number, street address, or date of birth appears in any page.
- No internal project names, repository links, or customer names appear on the detail pages.
- Every link works, and the pages read correctly in all three languages.
