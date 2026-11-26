# mhs.mn — Material Handling Systems website

One-page website in three languages (Mongolian, English, Chinese) for Material Handling Systems LLC, published on Cloudflare Pages (project `mhs-mn`, direct upload, since 7 Nov 2026) at https://mhs.mn (Mongolian), https://mhs.mn/en/ (English) and https://mhs.mn/zh/ (Chinese).

## What's where

```
docs/                      the website source: the only place to edit
  index.html               the whole site (HTML, CSS and JS in one file, all three languages)
  photos/                  site photos (JPG)
  fonts/                   the site's fonts (woff2, SIL Open Font License texts included)
  CNAME                    custom domain mhs.mn, left from GitHub Pages (do not delete)
  404.html                 the not-found page
  _headers                 Cloudflare Pages header rules (keeps mhs-mn.pages.dev out of search)
  robots.txt
  sitemap.xml
  llms.txt                 plain-text summary of the business for AI tools (keep its facts in step with the page)
  ef8d0dd29fefc4380d8930910c1606e7.txt   IndexNow key that lets the site ask Bing to crawl it (do not delete)
tools/build_site.py        turns docs/ into the published site (run it before each upload to Cloudflare)
.github/workflows/pages.yml  old GitHub Pages publish; manual only, not used since 7 Nov 2026
tools/check_live.py        checks the live site against a build
.github/workflows/live-check.yml  old scheduled check; manual only, not used since 7 Nov 2026
README.md                  this file (not published)
CLAUDE.md                  editing rules for Claude (not published)
```

## How publishing works

**Commits here publish nothing.** The site is built locally with `python3 tools/build_site.py docs _site` and `_site/` is uploaded to Cloudflare Pages (see CLAUDE.md and `.claude/skills/mhs-site-change/cf_deploy.md`). The build copies `docs/` and adds:

- smaller copies of the photos, so phones download a photo that fits their screen instead of the full-size file;
- the English page `https://mhs.mn/en/` and the Chinese page `https://mhs.mn/zh/`, made automatically from `docs/index.html` (that language's text, title and link preview). There is no separate English or Chinese file to edit;
- links that tell search engines the three pages are the same site in three languages;
- one language per page: the Mongolian page keeps only the Mongolian text, the English page only the English and the Chinese page only the Chinese, so search engines and AI tools never read them mixed together. `docs/index.html` keeps all three.

## Hosting (since 7 Nov 2026)

- **Cloudflare Pages**, project `mhs-mn`, deployed by direct upload of `_site/` (Workers & Pages → mhs-mn → Create deployment → Production). Custom domains mhs.mn and www.mhs.mn (www redirects to mhs.mn). The test address mhs-mn.pages.dev is kept out of search by `docs/_headers`; `docs/404.html` is the not-found page.
- DNS for mhs.mn is on Cloudflare (registrar: Datacom). MX and TXT records run the company email — leave them alone.
- The email-security policy (mta-sts.mhs.mn) is a separate Cloudflare Pages project, `mhs-mta-sts`.
- Until 7 Nov 2026 the site was on GitHub Pages. After the GitHub account suspension the owner moved it and decided to keep hosting and automation off GitHub. The two workflows in `.github/workflows/` are kept for reference and run only by hand; don't use them.

## Updating the site

1. Edit `docs/index.html` on GitHub (open the file → pencil icon → Commit changes). All three languages live in this one file: each text appears three times, in `<span lang="mn">`, `<span lang="en">` and `<span lang="zh">`.
2. To change a photo, upload the new photo into `docs/photos/` with **exactly the same file name** as the old one (Add file → Upload files, then Commit). The phone-size copies are made automatically. Use a JPG about 2000 px wide or less, and make sure no customer names or logos are visible.
3. Committing here does not change the live site. Build `_site/` and upload it to Cloudflare Pages (see `.claude/skills/mhs-site-change/cf_deploy.md`), or ask Claude to do it.
4. When content changes, update the three `<lastmod>` dates in `docs/sitemap.xml`.
5. If you change a phone number, the email, the address, the hours, the system counts or the services, change them in `docs/llms.txt` and in the `application/ld+json` block near the top of `docs/index.html` too.

Mongolian opens at https://mhs.mn, English at https://mhs.mn/en/ and Chinese at https://mhs.mn/zh/; the МН / EN / CN buttons switch between them. Old links `https://mhs.mn/?lang=en` and `https://mhs.mn/#en` still open the English page, and `?lang=zh` / `#zh` the Chinese one.
