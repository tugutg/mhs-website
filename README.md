# mhs.mn — Material Handling Systems website

One-page bilingual (Mongolian / English) website for Material Handling Systems LLC, published with GitHub Pages at https://mhs.mn (Mongolian) and https://mhs.mn/en/ (English).

## What's where

```
docs/                      the website source: the only place to edit
  index.html               the whole site (HTML, CSS and JS in one file, both languages)
  photos/                  site photos (JPG)
  fonts/                   the site's fonts (woff2, SIL Open Font License texts included)
  CNAME                    custom domain: mhs.mn (do not delete)
  robots.txt
  sitemap.xml
tools/build_site.py        turns docs/ into the published site (runs on GitHub, not on your computer)
.github/workflows/pages.yml  runs the build and publishes the site after every change to main
README.md                  this file (not published)
CLAUDE.md                  editing rules for Claude (not published)
```

## How publishing works

Every commit to `main` starts the **Publish site** workflow (Actions tab). It copies `docs/` and adds:

- smaller copies of the photos, so phones download a photo that fits their screen instead of the full-size file;
- the English page `https://mhs.mn/en/`, made automatically from `docs/index.html` (English text, title and link preview). There is no separate English file to edit;
- links that tell search engines the two pages are the same site in two languages.

The site is live a minute or two after the workflow turns green. If it turns red, open the run to see why; you can start it again with **Run workflow**. Lines starting with `WARNING` in the build log mean the build met something it did not recognise and published that part unchanged — the site still works.

## Hosting

- GitHub Pages: Settings → Pages → Build and deployment → Source: **GitHub Actions**. Custom domain `mhs.mn`, Enforce HTTPS on.
- DNS for mhs.mn is managed at Datacom:
  - A `@` → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
  - CNAME `www` → `tugutg.github.io`
  - MX and TXT records run the company email — leave them alone.

## Updating the site

1. Edit `docs/index.html` on GitHub (open the file → pencil icon → Commit changes). Both languages live in this one file: each text appears twice, once in `<span lang="mn">` and once in `<span lang="en">`.
2. To change a photo, upload the new photo into `docs/photos/` with **exactly the same file name** as the old one (Add file → Upload files, then Commit). The phone-size copies are made automatically. Use a JPG about 2000 px wide or less, and make sure no customer names or logos are visible.
3. The live site updates when the Publish site workflow finishes (Actions tab).
4. When content changes, update both `<lastmod>` dates in `docs/sitemap.xml`.

Mongolian opens at https://mhs.mn and English at https://mhs.mn/en/; the МН / EN buttons switch between them. Old links `https://mhs.mn/?lang=en` and `https://mhs.mn/#en` still open the English page.
