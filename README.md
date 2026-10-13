# mhs.mn — Material Handling Systems website

One-page bilingual (Mongolian / English) website for Material Handling Systems LLC, published with GitHub Pages at https://mhs.mn.

## What's where

```
docs/               everything GitHub Pages publishes
  index.html        the whole site (HTML, CSS and JS in one file)
  photos/           site photos (JPG)
  CNAME             custom domain: mhs.mn (do not delete)
  robots.txt
  sitemap.xml
README.md           this file (not published)
CLAUDE.md           editing rules for Claude (not published)
```

## Hosting

- GitHub Pages: Settings → Pages → Deploy from a branch → `main` / `/docs`, custom domain `mhs.mn`, Enforce HTTPS on.
- DNS for mhs.mn is managed at Datacom:
  - A `@` → `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
  - CNAME `www` → `tugutg.github.io`
  - MX and TXT records run the company email — leave them alone.

## Updating the site

1. Edit `docs/index.html` on GitHub (open the file → pencil icon → Commit changes), or replace a photo in `docs/photos/` with a file of the same name.
2. The live site updates a few minutes after the commit (progress shows in the Actions tab).
3. When content changes, update `<lastmod>` in `docs/sitemap.xml`.

Mongolian opens by default; `https://mhs.mn/?lang=en` or `https://mhs.mn/#en` opens English.
