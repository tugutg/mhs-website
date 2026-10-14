# Notes for Claude — mhs.mn website

Static one-page site for Material Handling Systems LLC (MHS). `docs/` is the source. On every push to `main`, GitHub Actions (`.github/workflows/pages.yml`) runs `tools/build_site.py`, which turns `docs/` into the published site, and deploys it to https://mhs.mn (Settings → Pages → Source: "GitHub Actions"). After every successful deploy, every Monday and on demand, `.github/workflows/live-check.yml` runs `tools/check_live.py`. It checks that the live pages are exactly that build, that every file loads, and that the linked YouTube videos still exist; it never changes the site.

## Rules

- Keep it one static page: `docs/index.html` with inline CSS and JS, no frameworks or trackers. It is the only page anyone edits and must keep working on its own (opened straight from the repository it shows every photo and both languages, with the switch working in place).
- The build is the only build step: Python + Pillow, no other dependencies. It copies `docs/` as it is and adds:
  - phone-size copies of every photo in a `<figure class="slot">` (`photos/NAME-800w.jpg` …) with `srcset`/`sizes` on its `<img>`, plus a centre crop of the hero for phones up to 430 px (`photos/NAME-phone.jpg`, through `<picture>`; it shows the same part of the photo at the same scale; `HERO_PHONE_MAX = 0` turns it off);
  - `en/index.html`: the same page with English as the default (`lang`, `data-lang`, `<title>` and `og:title` from `data-title-en`, meta and og description from the English text of the hero's `.lead`, `og:image:alt` from the hero's `data-alt-en`, `og:locale`, `og:url` and canonical on `https://mhs.mn/en/`, relative paths moved up one folder);
  - hreflang links on both pages (mn → `https://mhs.mn/`, en → `https://mhs.mn/en/`, x-default → `https://mhs.mn/`), `data-href` on the MN/EN buttons so they switch address, and a small `<head>` script that sends the old `?lang=en` / `#en` links and a saved English choice to `/en/`.
- Never commit generated files to `docs/` (no `docs/en/`, no `-800w`/`-phone` photo copies) — the build makes them on every deploy. `_site/` is the local build output and is ignored.
- The build must never fail because the page changed: anything it does not recognise is published unchanged with a `WARNING` line in the Actions log. Keep it that way, and read the log after changes to the page structure.
- Photo boxes: `sizes` comes from the slot boxes measured in Chromium (`HERO_HEIGHTS` and the card/tall numbers in `tools/build_site.py`). If you change slot CSS (aspect-ratio, grid columns, gutters, `.wrap` width, hero padding or hero text length by a lot), re-measure and update those numbers, then check which `srcset` candidate is picked at DPR 1, 2 and 3. A new kind of slot is left without `srcset` (with a warning) until the build knows its box.
- Fonts are self-hosted in `docs/fonts/` (copies of the Google Fonts files from the @fontsource packages, SIL OFL; keep the `LICENSE-*.txt` files). The `@font-face` rules are inline at the top of the `<style>` with `unicode-range` and `font-display: swap`. Mongolian needs the cyrillic and cyrillic-ext subsets (Ө ө Ү ү) plus latin. Preload only the two first-screen files (Fira Sans Extra Condensed 800 and IBM Plex Sans, cyrillic); the build swaps them to latin on `/en/`. No Google Fonts links.
- Bilingual: every visible string exists twice, as `<span lang="mn">…</span><span lang="en">…</span>`. Mongolian is the default (`data-lang="mn"` on `.site`). Placeholders, alt text and aria labels use `data-ph-mn/en`, `data-alt-mn/en` and `data-aria-mn/en`. Keep `data-title-mn/en` on `.site` and the English span in the hero's `.lead` — the English page's title and description come from them.
- Show only DAFO and SENNEBOGEN as official partners.
- Never name customers — in text, alt text or photos. References stay as machine types, models and counts. Before adding a photo, check machine bodies and truck canopies for painted company names or logos and remove them: the repository is public and its history keeps every file ever committed.
- Photos live in `docs/photos/` and are linked with relative paths (`photos/…`). Keep them about 2000 px wide or less and compressed (JPEG; the build only makes copies of JPEGs); use `loading="lazy"` below the first screen. The owner replaces a photo by uploading a file with the same name; nothing else is needed.
- `docs/og-image.jpg` is the link-preview picture (1200×630, cropped from the hero photo, used by `og:image` on both pages). Regenerate it if the hero photo changes, and keep `<title>`, `og:title` and `og:description` in step with the page's wording.
- Keep `data-build="live"` on the `.site` div.
- Videos are plain links to YouTube (`.vid` tiles: play icon, bilingual title, `target="_blank" rel="noopener"`, hidden "opens in a new tab" text), never embedded players, which would load Google's scripts and cookies.
- The quote form only builds an email (mailto) — there is no server. Keep it that way unless the user asks for a form service.
- Do not delete `docs/CNAME` (`mhs.mn`). Keep URLs in `robots.txt` and `sitemap.xml` on `https://mhs.mn/`; the sitemap lists `/` and `/en/` with hreflang alternates — bump both `<lastmod>` when content changes.
- Before committing, run `python3 tools/build_site.py docs _site`, serve `_site/` (e.g. `python3 -m http.server -d _site`) and open `/` and `/en/` at desktop and phone widths: every image loads, no warnings, the MN/EN switch changes address.

## Working on this repo

- Other Claude sessions push to `main` in parallel. Before starting, `git fetch` and read `git log origin/main` and the open PRs for overlapping work. Do it again before pushing, and re-read this file after fetching.
- For any change (scope question, edit, build, browser check, PR, merge, deploy check), follow `.claude/skills/mhs-site-change/SKILL.md`. It also has the scripts `site_text.py` (find/replace with language and section), `check.cjs` (browser checks) and `deploy_wait.sh`. Merging follows the owner's rule below.

## Owner's decisions (don't reopen)

- The owner's Mongolian text goes in verbatim. A possible typo is offered as a fix option in the merge question, once the PR is open, never fixed silently. «эрсдлээс» (hero heading) is spelled on purpose; leave the page's other forms («эрсдэлийн», «эрсдэлтэй») as they are, and don't make them match either way.
- Claude writes the English side. A wording change to the Mongolian alone leaves the English as it is. If the change alters a fact (number, model, name, contact, date), ask whether the English follows.
- DAFO and SENNEBOGEN: MHS is their "official dealer" («Албан ёсны дилер»), never "partner". The rule above means only these two brands are shown. The service schedule names only the 10-year major service, with no 5-year actuator replacement. The warranty text says «DAFO Vehicle».
- The extinguishing agent is «Форрекс» in the DAFO video title, the key-data row label and the About list. Elsewhere «Forrex EVO бодис» stays in Latin, and the English stays "agent" / "Forrex EVO". «галын хор» is fine in the owner's own Forrex EVO paragraph.
- Titles (`data-title-mn/en` and `<title>`): MN «DAFO гал унтраах систем, SENNEBOGEN | Материал Хандлинг Системс ХХК», EN "DAFO Fire Suppression, SENNEBOGEN in Mongolia | MHS LLC".
- No Facebook or YouTube channel links on the site. The videos stay plain YouTube links: five `.vid` tiles (three DAFO, two SENNEBOGEN), plus the clean-up video linked again in the FAQ answer (`a.vlink`), so six links show in each language.
- Leave as they are: the Mongolian aria labels, and the English FAQ sentence "… at 10 years the piston and agent replaced …".
- **Merging (standing rule since 14 Oct 2026):**
  - **Small wording changes merge without asking,** once the build has 0 warnings and the skill's `check.cjs` passes. Tell the owner afterwards what went live. Small wording means only visible text: words, or a sentence or plain paragraph added or removed in the existing style, plus matching alt, aria, placeholder and title text and the sitemap dates.
  - **Everything else asks first:** new kinds of elements, links or videos, CSS, JS, photos, fonts, `tools/`, workflows, CLAUDE.md and skills. So does any change with an open question (scope, typo, or whether the English follows).
- Search Console is verified for mhs.mn as a Domain property (DNS), so no verification tag is needed.
- A "DAFO Монголиа" listing on huree.mn has nothing to do with MHS or DAFO. Ignore it.
