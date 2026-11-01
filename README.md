# Luis Felipe Henao: personal site

A one-page personal site for Luis Felipe Henao, Senior Data Engineer, with two detail pages for private projects. It is written in Spanish, English, and French, and has no build step and no dependencies.

**Live:** https://felipeache.github.io (https://henao.me once the custom domain is active)

## Pages

| File | Contents |
|---|---|
| `index.html` | Home page: hero, about, skills, experience, projects, education, contact |
| `projects/deduplication.html` | Detail page for the deduplication pipeline |
| `projects/validation.html` | Detail page for the agentic validation website |
| `projects/customer-identity-delivery.html` | Detail page for the customer identity delivery pipeline |
| `projects/retail-pos-ingestion.html` | Detail page for the retail point-of-sale ingestion pipeline |
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

## Analytics

The site uses [GoatCounter](https://www.goatcounter.com), a free analytics service that sets no cookies. The dashboard is at https://felipeache.goatcounter.com.

What it records:
- page views and unique visitors per day, counted from a daily hash, not from a person's identity
- referrers (LinkedIn, Google, direct), countries, and browsers, in aggregate
- time on page, as buckets (under 10 s, 10–60 s, 1–3 min, over 3 min), sent as events when the visitor leaves a page
- navigation paths, as `nav/<from> > <to>` events, counted when a visit comes from another page on the site
- entry pages, as `entry/<path>` events, counted when a visit has no referrer from the site (direct or external links)
- link clicks, as `click/<label>` events: `linkedin`, `github`, `strava`, `email`, `contact-button`, `project-deduplication`, `project-validation`, `back`, `section/<name>`, or `other`

What it does not record: names, email addresses, IP addresses, or anything that identifies a person. Each page has three pieces: the GoatCounter script in `<head>`, and two inline scripts before `</body>`, one for time on page and one for navigation and clicks. If you add a page, copy all three. The scripts store nothing on the device: no cookies, `localStorage`, or `sessionStorage`.

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
