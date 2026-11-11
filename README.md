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

The site uses [Umami Cloud](https://cloud.umami.is) via `https://cloud.umami.is/script.js` with website id `a1116ae4-e920-4ce0-a14b-6a8459cb377e`. Custom events go through `assets/analytics.js` (`siteTrack`).

What it records automatically:
- page views and unique visitors
- referrers (LinkedIn, Google, direct), countries, browsers, OS, and devices, in aggregate

Custom events (via `siteTrack`):
- time on page, as buckets (under 10 s, 10–60 s, 1–3 min, over 3 min), sent when the visitor leaves a page
- navigation paths, as `nav/<from> > <to>` when a visit comes from another page on the site
- entry pages, as `entry/<path>` when a visit has no referrer from the site (direct or external links)
- link clicks, as `click/<label>`: `linkedin`, `github`, `strava`, `email`, `cv-en`, `cv-es`, `cv-fr` (from the CV file name), `contact-button`, `project-deduplication`, `project-validation`, `project-customer-identity`, `project-retail-pos`, `training`, `back`, `section/<name>`, or `other`
- language switch: `click/lang-en` / `click/lang-es` / `click/lang-fr` (flag clicks only)
- theme toggle: `click/theme-light` / `click/theme-dark`
- Christmas toggle: `click/christmas-on` / `click/christmas-off`

CV downloads: `click/cv-xx` is sent as Umami event `cv-download` with data `{ language: "en" | "es" | "fr" }`, so the Events view shows which CV was downloaded. Middle-clicks on the CV button are counted too. A CV opened from a direct link to the PDF outside the site (for example a shared `https://henao.me/assets/CV_Luis_Felipe_Henao_EN.pdf`) cannot be counted, because analytics scripts only run on HTML pages.

What it does not record: names, email addresses, IP addresses, or anything that identifies a person. Each page loads the Umami script and `assets/analytics.js` in `<head>`, plus two inline scripts before `</body>` (time on page; navigation and clicks). If you add a page, copy those.

The training charts use [Chart.js](https://www.chartjs.org) 4.5.1, stored in `vendor/chart.umd.min.js` (MIT licence, copy in `vendor/CHART_JS_LICENSE.md`).

## Training dashboard (Strava)

`training.html` shows the last 12 months of training from Strava: totals, monthly distance, sessions per week, activity mix, personal records, and the ten most recent activities.

How it works:
- `scripts/sync_strava.py` fetches the activities and writes only aggregates to `data/training.js`. Routes, maps, coordinates, and activity names are never saved.
- `.github/workflows/strava-sync.yml` runs the script once a day at 21:00 Paris time (20:00 UTC; 22:00 in summer, when UTC shifts), and can be started by hand from the Actions tab (Run workflow). It commits `data/training.js` only when the data changed, and GitHub Pages then rebuilds the site.
- The dashboard reads `data/training.js` with a normal script tag, so it also opens from a local file.

One-time setup:
1. Create a Strava API application at https://www.strava.com/settings/api. Note the Client ID and Client Secret.
2. Authorise the app once in a browser, with the `activity:read` scope (use `activity:read_all` if private activities should be included): `https://www.strava.com/oauth/authorize?client_id=CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read`. Copy the `code` value from the address you are redirected to.
3. Exchange the code for a refresh token: `curl -X POST https://www.strava.com/oauth/token -d client_id=CLIENT_ID -d client_secret=CLIENT_SECRET -d code=CODE -d grant_type=authorization_code`. Keep the `refresh_token` from the response.
4. In the repository's Settings → Secrets and variables → Actions, add `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, and `STRAVA_REFRESH_TOKEN`.
5. Run the workflow once from the Actions tab.

Strava's API agreement limits how its data may be stored and shown. Check that a public display of these aggregates is allowed before publishing, and keep the "Data from Strava" credit on the page.

## Metro dashboard (WIP)

`metro.html` shows live Paris metro line status (normal / info / disrupted / blocked), per-line disruption counts by month and year, and the longest clear-day streak. It is **not linked from the home page yet**—open `/metro.html` directly while developing.

How it works:
- `scripts/sync_metro.py` calls the Île-de-France Mobilités [PRIM](https://prim.iledefrance-mobilites.fr) metro `line_reports` API and writes `data/metro.js` plus `data/metro_state.json` (daily flags and first-seen disruption IDs).
- `.github/workflows/metro-sync.yml` runs every two hours (and on `workflow_dispatch` / push to `main`). It commits only when those data files change.
- History starts at go-live: PRIM has no multi-year archive, so monthly/yearly counts and streaks grow as the sync runs.
- Information-only alerts do not count as a disruption day; perturbed/blocked statuses do.

One-time setup:
1. Create a PRIM account and subscribe to the Messages Info Trafic API at https://prim.iledefrance-mobilites.fr.
2. Copy your API token.
3. In the repository's Settings → Secrets and variables → Actions, add `PRIM_API_KEY`.
4. Locally: `PRIM_API_KEY=... python3 scripts/sync_metro.py` (Python 3.9+ recommended; CI uses 3.12).
5. Run the **Sync metro disruptions** workflow once from the Actions tab.

Credit Île-de-France Mobilités / PRIM on the page. This project is not affiliated with RATP or IDFM.

## Pre-rendered English content

Crawlers, LinkedIn previews and ATS scrapers do not run JavaScript, so `index.html` carries a baked copy of the rendered English sections between `<!-- prerender:start -->` and `<!-- prerender:end -->`. The browser still re-renders everything on load, so Spanish and French are unaffected. After you change text in `T` or the render functions, refresh the copy and commit `index.html`:

```bash
python3 scripts/prerender.py   # needs Google Chrome; set CHROME to override the macOS path
```

## Languages

Spoken languages appear twice: a short row in the hero (the three strong languages, linking down) and a Languages section (all four, one card each with a level pill and a decorative five-segment indicator). Both are rendered from `T.*.languages` in `index.html`: each item has its own-language name, the page-language name, a level word, an optional CEFR code (`cefr`), the indicator value (`bar`) and whether it shows in the hero (`hero`). Order is fixed (Spanish, French, English, Italian), the same as the CVs. Levels are self-assessed, so keep the site, the CVs and LinkedIn wording the same. Hovering (or tapping) a card shows a greeting bubble in that card's language, from `hello`.

## CV downloads

The home page offers the CV as a PDF in each language (`assets/CV_Luis_Felipe_Henao_EN.pdf`, `_FR.pdf`, `_ES.pdf`). The text lives in `cv/CV_EN.md`, `cv/CV_FR.md` and `cv/CV_ES.md`, and the PDFs are generated from it:

```bash
pip install fpdf2 pymupdf   # PyMuPDF is optional, used only for the sanity check
python3 scripts/build_cv.py        # all three, or e.g. `python3 scripts/build_cv.py fr`
```

The script uses the macOS Arial fonts. The public CV has no phone number or street address, per "Checks before publishing". Edit the markdown, rebuild, and commit both the markdown and the PDFs. The download link is analytics label `cv-en` / `cv-es` / `cv-fr` (Umami: `cv-download` + `language`).

## Christmas mode

A tree button in the header (next to the theme toggle) turns on a Christmas look. It is off by default and the choice is saved in `localStorage` under `site-xmas`.

- `assets/christmas.js` and `assets/christmas.css` hold everything, and every page loads them with two tags in `<head>` (`../assets/...` on the project pages). If you add a page, copy both tags.
- The button is festive red while off (it pulses until a first use) and green while on, with a hover/focus tooltip in EN/ES/FR.
- When on: red and green accent colours (both themes), slow, time-based snow in red, white and green, a string of lights under the header, a greeting line, a Santa hat on the portrait (home page), and three emoji characters floating in each bottom corner (snowman, Santa and gift on the left; gift, reindeer and tree on the right). The snow, the twinkling and the bobbing stop for visitors who prefer reduced motion.
- When off, all of it is removed, and the page is the normal site. The pre-rendered copy in `index.html` is always the normal site.
- Analytics labels: `click/christmas-on` and `click/christmas-off`.
- To remove the feature, delete the two asset files and the two `<head>` tags on each page.

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
