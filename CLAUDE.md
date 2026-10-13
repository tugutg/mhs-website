# Notes for Claude — mhs.mn website

Static one-page site for Material Handling Systems LLC (MHS). GitHub Pages publishes `docs/` from the `main` branch to https://mhs.mn.

## Rules

- Keep it one static page: `docs/index.html` with inline CSS and JS. No build step, frameworks or trackers.
- Bilingual: every visible string exists twice, as `<span lang="mn">…</span><span lang="en">…</span>`. Mongolian is the default (`data-lang="mn"` on `.site`). Placeholders, alt text and aria labels use `data-ph-mn/en`, `data-alt-mn/en` and `data-aria-mn/en`.
- Show only DAFO and SENNEBOGEN as official partners.
- Never name customers — in text, alt text or photos. References stay as machine types, models and counts. Before adding a photo, check machine bodies and truck canopies for painted company names or logos and remove them: the repository is public and its history keeps every file ever committed.
- Photos live in `docs/photos/` and are linked with relative paths (`photos/…`). Keep them about 2000 px wide or less and compressed; use `loading="lazy"` below the first screen.
- `docs/og-image.jpg` is the link-preview picture (1200×630, cropped from the hero photo, used by `og:image`). Regenerate it if the hero photo changes, and keep `<title>`, `og:title` and `og:description` in step with the page's wording.
- Keep `data-build="live"` on the `.site` div.
- The quote form only builds an email (mailto) — there is no server. Keep it that way unless the user asks for a form service.
- Do not delete `docs/CNAME` (`mhs.mn`). Keep URLs in `robots.txt` and `sitemap.xml` on `https://mhs.mn/`, and bump `<lastmod>` when content changes.
- Before committing, open the page at desktop and phone widths in both languages and check that every image loads.
