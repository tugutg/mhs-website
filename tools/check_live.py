#!/usr/bin/env python3
"""Check the live site (standard library only; runs in GitHub Actions, see .github/workflows/live-check.yml).

  python3 tools/check_live.py [--built _site] [--site https://mhs.mn] [--wait 240] [--no-youtube]

- /, /en/, /robots.txt and /sitemap.xml answer 200, and /en redirects to /en/.
- With --built DIR: the live / and /en/ are byte for byte the pages in DIR (the build of the same commit).
  Right after a deploy the CDN may still serve the old pages, so this retries for up to --wait seconds.
  If main has moved on since (a newer commit was published), a mismatch is only a warning: the Live check
  of that newer commit covers the site.
- Every photo, font and other file the two pages use (og-image.jpg too) answers 200.
- Every linked YouTube video is still there: YouTube's oEmbed answers 200 (and gives its title).
  404 means the video was removed or the link is wrong (a problem). 401/403 means private or embedding
  turned off (a warning: the link may still open on youtube.com). A YouTube link in a form this script
  doesn't know is listed as a warning, not skipped.
Writes a summary for the Actions run page when $GITHUB_STEP_SUMMARY is set. Exit code 1 on any problem.
"""
import argparse
import html
import http.client
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = {'User-Agent': 'mhs-live-check (+https://github.com/tugutg/mhs-website)'}
problems, warnings, notes = [], [], []


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def get(url, follow=True, tries=3):
    """(status, headers, body bytes); status 0 when the network failed after all tries."""
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    for i in range(tries):
        try:
            with opener.open(urllib.request.Request(url, headers=UA), timeout=20) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500 or i == tries - 1:
                return e.code, e.headers, e.read()
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:  # HTTPException: a cut-off answer
            if i == tries - 1:
                return 0, {}, str(e).encode()
        time.sleep(3 * (i + 1))


def local_urls(page_html, page_url, site):
    """Same-site files a page uses: src, href, srcset and url() in its CSS."""
    found = set()
    page_html = re.sub(r'<!--.*?-->', '', page_html, flags=re.S)  # examples in comments are not real files
    refs = re.findall(r'\s(?:src|href)="([^"]+)"', page_html)
    for srcset in re.findall(r'\ssrcset="([^"]+)"', page_html):
        refs += [c.strip().split()[0] for c in srcset.split(',') if c.strip()]
    refs += [u.strip('\'"') for u in re.findall(r'url\(([^)]+)\)', page_html)]
    refs += re.findall(r'<meta\s[^>]*property="og:image"[^>]*content="([^"]+)"', page_html)  # link preview
    for ref in refs:
        ref = html.unescape(ref)
        if ref.startswith(('#', 'mailto:', 'tel:', 'data:', 'javascript:')):
            continue
        url = urllib.parse.urljoin(page_url, ref).split('#')[0]
        if url.startswith(site + '/'):
            found.add(url)
    return found


def youtube_links(page_html):
    """(video ids, links whose form is unknown) for every link to YouTube on a page."""
    ids, unknown = set(), set()
    for link in re.findall(r'href="(https?://(?:[\w-]+\.)?(?:youtube\.com|youtu\.be)/[^"]*)"', page_html):
        link = html.unescape(link)
        m = re.search(r'(?:youtu\.be/|[?&]v=|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{11})', link)
        if m:
            ids.add(m.group(1))
        else:
            unknown.add(link)
    return ids, unknown


def main_moved_on(sha):
    """True when main is no longer at sha: a newer commit was published since, and its own Live check covers it."""
    if not re.fullmatch(r'[0-9a-f]{40}', sha or ''):
        return False
    try:
        out = subprocess.run(['git', 'ls-remote', 'origin', 'refs/heads/main'],
                             capture_output=True, text=True, timeout=30).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return False
    return bool(out) and out[0] != sha


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--site', default='https://mhs.mn')
    ap.add_argument('--built', help='folder with the build of the deployed commit (e.g. _site)')
    ap.add_argument('--wait', type=int, default=240, help='seconds to wait for the CDN to serve the new pages')
    ap.add_argument('--no-youtube', action='store_true', help='skip the YouTube checks')
    args = ap.parse_args()
    site = args.site.rstrip('/')
    stamp = os.environ.get('LIVE_CHECK_STAMP') or os.environ.get('GITHUB_SHA') or str(int(time.time()))

    pages = {}
    deadline = time.time() + args.wait  # one budget for both pages: they are deployed together
    for path in ('/', '/en/'):
        url = site + path
        want = None
        if args.built:
            with open(os.path.join(args.built, path.strip('/'), 'index.html'), 'rb') as f:
                want = f.read()
        while True:
            # a new query string on every try: the CDN caches each address (query included) for a few minutes,
            # so asking again for the same address could only return the same, possibly old, copy
            status, _, body = get('%s?live-check=%s-%d' % (url, stamp, time.time()))
            if status == 200 and (want is None or body == want):
                break
            if time.time() > deadline:
                break
            time.sleep(15)
        if status != 200:
            problems.append('%s answered %s' % (url, status or 'no connection: ' + body.decode(errors='replace')[:120]))
            continue
        if want is not None and body != want:
            if main_moved_on(stamp):
                warnings.append('%s is not the build of %s, but main has moved on since; the Live check of the newer '
                                'commit covers it' % (url, stamp[:7]))
            else:
                problems.append('%s is not the page built from this commit (still the old one after %d s?)' % (url, args.wait))
        else:
            notes.append('%s: 200%s' % (url, ', same as the build' if want is not None else ''))
        pages[path] = body.decode('utf-8', errors='replace')

    for path in ('/robots.txt', '/sitemap.xml'):
        status, _, _ = get(site + path)
        (notes if status == 200 else problems).append('%s%s: %s' % (site, path, status))
    status, headers, _ = get(site + '/en', follow=False)
    location = headers.get('Location', '') if headers else ''
    if status in (301, 302, 308) and location.rstrip('/').endswith('/en'):
        notes.append('%s/en redirects to /en/ (%s)' % (site, status))
    else:
        problems.append('%s/en should redirect to /en/, got %s %s' % (site, status, location))

    files = set()
    for path, body in pages.items():
        files |= local_urls(body, site + path, site)
    bad = []
    for url in sorted(files):
        status, _, _ = get(url)
        if status != 200:
            bad.append('%s (%s)' % (url, status))
    if bad:
        problems.append('%d of %d files do not load: %s' % (len(bad), len(files), ', '.join(bad[:10])))
    else:
        notes.append('all %d files used by the pages load' % len(files))

    vids, unknown = set(), set()
    for body in pages.values():
        found, odd = youtube_links(body)
        vids |= found
        unknown |= odd
    for link in sorted(unknown):
        warnings.append('YouTube link not checked (unknown form): %s' % link)
    if not args.no_youtube:
        for vid in sorted(vids):
            watch = 'https://www.youtube.com/watch?v=' + vid
            status, _, body = get('https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote(watch, safe=''))
            if status == 200:
                try:
                    title = json.loads(body)['title']
                except (ValueError, KeyError, TypeError):
                    warnings.append('YouTube %s: oEmbed answered 200 but not with its usual JSON (a consent or bot '
                                    'page?); check that %s opens' % (vid, watch))
                    continue
                notes.append('YouTube %s: «%s»' % (vid, title))
            elif status in (401, 403):
                warnings.append('YouTube %s is private or has embedding turned off (%s); check that %s opens' % (vid, status, watch))
            elif status in (400, 404):
                problems.append('YouTube %s was not found (%s): removed, or a wrong link' % (vid, status))
            else:
                warnings.append('YouTube %s could not be checked (%s)' % (vid, status))

    lines = ['## Live check of %s' % site, '']
    lines += ['- ❌ ' + p for p in problems] + ['- ⚠️ ' + w for w in warnings] + ['- ✅ ' + n for n in notes]
    report = '\n'.join(lines) + '\n'
    print(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(report)
    for w in warnings:
        print('::warning::' + w)
    for p in problems:
        print('::error::' + p)
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
