#!/usr/bin/env python3
"""Turn docs/ into the published mhs.mn site.

    python tools/build_site.py [SOURCE_DIR] [OUTPUT_DIR]      (defaults: docs _site)

GitHub Actions runs this on every push to main that changes docs/ or the build (.github/workflows/pages.yml) and publishes the output.
Needs Python 3.9+ and Pillow, nothing else. docs/ stays the only thing anyone edits:

  * Everything in docs/ is copied as it is (CNAME, robots.txt, sitemap.xml, og-image.jpg, fonts, photos).
  * Photos in a <figure class="slot"> get smaller copies (photos/NAME-800w.jpg, ...) and their <img> gets
    srcset and sizes, so phones download a file that fits their screen. The hero also gets a centre crop
    for portrait phones (photos/NAME-phone.jpg) through <picture>; it shows the same part of the photo at
    the same scale, from a smaller file.
  * en/index.html is the same page with English as the default language and its own address.
  * Both pages get hreflang links, and the MN/EN buttons switch between the two addresses.

The build never fails because the page changed: anything it does not recognise (a missing photo, a new
kind of slot, a missing tag) is published unchanged with a WARNING line in the log.
"""

import html
import math
import os
import re
import shutil
import sys
from html.parser import HTMLParser

from PIL import Image, ImageOps, JpegImagePlugin

SITE = "https://mhs.mn/"
EN_DIR = "en"

# Widths (px) of the smaller copies. Close steps matter: Chrome may pick a copy up to
# sqrt(step) below what a high-density screen needs, so steps stay at 1.2-1.33x.
WIDTHS = [480, 640, 800, 1000, 1200, 1440, 1600, 1920, 2400]
# sizes is set 10% above the measured box so that Chrome's choice never falls below what is shown.
MARGIN = 1.10
MAX_QUALITY = 80  # the hero is saved at q80, the other photos at q75; copies never go above the original

# Rendered photo boxes, measured in Chromium in both languages (CSS px; vw = viewport width).
#   card: 16:10 box, one column up to 900px (at most 92vw), three columns up to 1200px (at most 30vw), then 356px.
#   tall: one column up to 900px, 16:11 box (at most 92vw); two columns above, a 4:5 box at most 42vw / 504px wide.
#   hero: full width; its height follows the text, so it is listed per viewport width (the tallest of MN and EN).
HERO_HEIGHTS = [(320, 950), (360, 885), (400, 860), (430, 815), (560, 775), (620, 565),
                (760, 555), (900, 590), (1100, 650), (1300, 790), (None, 815)]
# Portrait phones up to this width get the hero's centre crop. Their hero box is at most 0.64 as wide as
# it is tall; the crop keeps 15% more width than that so it always covers the box, which makes
# object-fit: cover show the same part of the photo at the same scale as the full file (placement can differ
# by under one device pixel from rounding). Set HERO_PHONE_MAX = 0 to publish without the crop.
HERO_PHONE_MAX = 430
HERO_PHONE_ASPECT = 0.64 * 1.15

warnings = []


def warn(msg):
    warnings.append(msg)
    print("WARNING: " + msg)


# ---------------------------------------------------------------- HTML helpers

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Tag:
    def __init__(self, name, attrs, start, end, ancestors):
        self.name, self.attrs, self.start, self.end, self.ancestors = name, dict(attrs), start, end, ancestors

    def cls(self):
        return (self.attrs.get("class") or "").split()


class Scanner(HTMLParser):
    """Lists every start tag with its position in the text and its open ancestors."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.text, self.tags, self.stack = text, [], []
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", text)]
        self.feed(text)
        self.close()

    def _offset(self):
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, name, attrs):
        start = self._offset()
        raw = self.get_starttag_text() or ""
        tag = Tag(name, attrs, start, start + len(raw), list(self.stack))
        self.tags.append(tag)
        if name not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, name, attrs):
        start = self._offset()
        raw = self.get_starttag_text() or ""
        self.tags.append(Tag(name, attrs, start, start + len(raw), list(self.stack)))

    def handle_endtag(self, name):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].name == name:
                del self.stack[i:]
                break


def set_attr(tag_text, name, value):
    """Set (or add) one attribute in the text of a start tag."""
    value = html.escape(value, quote=True)
    pattern = re.compile(r'(\s%s\s*=\s*)("[^"]*"|\'[^\']*\'|[^\s>]+)' % re.escape(name), re.I)
    if pattern.search(tag_text):
        return pattern.sub(lambda m: m.group(1) + '"%s"' % value, tag_text, count=1)
    end = -2 if tag_text.endswith("/>") else -1
    return tag_text[:end].rstrip() + ' %s="%s"' % (name, value) + tag_text[end:]


def apply_edits(text, edits):
    """edits: list of (start, end, replacement); applied from the end so offsets stay valid."""
    for start, end, new in sorted(edits, key=lambda e: e[0], reverse=True):
        text = text[:start] + new + text[end:]
    return text


def inner_text(text, tag):
    """Text content of an element whose start tag is `tag` (simple elements without nesting of the same tag)."""
    close = text.find("</%s>" % tag.name, tag.end)
    if close < 0:
        return ""
    raw = re.sub(r"<[^>]+>", "", text[tag.end:close])
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


# ---------------------------------------------------------------- photos

def is_relative(url):
    return bool(url) and not re.match(r"^([a-z][a-z0-9+.-]*:|/|#)", url, re.I)


def jpeg_quality(im):
    """Estimate the quality an existing JPEG was saved at (libjpeg scaling of the standard luminance table)."""
    std = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55, 14, 13, 16, 24, 40, 57, 69, 56,
           14, 17, 22, 29, 51, 87, 80, 62, 18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
           49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99]
    table = sorted((getattr(im, "quantization", None) or {}).get(0, []))
    if len(table) != 64:
        return MAX_QUALITY
    best = None
    for q in range(1, 101):
        scale = 5000 / q if q < 50 else 200 - 2 * q
        scaled = sorted(max(1, min(255, int((v * scale + 50) // 100))) for v in std)
        diff = sum(abs(a - b) for a, b in zip(scaled, table))
        if best is None or diff < best[0]:
            best = (diff, q)
    return best[1]


def save_jpeg(im, path, icc, **opts):
    kwargs = dict(optimize=True, progressive=True)
    if icc:
        kwargs["icc_profile"] = icc  # colour profile, not metadata: without it colours could shift
    kwargs.update(opts)
    im.save(path, "JPEG", **kwargs)


def px(value):
    return "%dpx" % math.ceil(value)


def vw(value):
    return "%dvw" % math.ceil(value * 100)


def sizes_for(kind, ar):
    """The sizes attribute: CSS px of image width needed to cover the slot with object-fit: cover."""
    m = MARGIN
    if kind == "card":
        f = max(1.0, ar / 1.6)
        return "(max-width: 900px) %s, (max-width: 1200px) %s, %s" % (vw(0.92 * f * m), vw(0.30 * f * m), px(356 * f * m))
    if kind == "tall":
        f1, f2 = max(1.0, ar / (16 / 11)), max(1.0, ar / 0.8)
        return "(max-width: 900px) %s, (max-width: 1200px) %s, %s" % (vw(0.92 * f1 * m), vw(0.42 * f2 * m), px(504 * f2 * m))
    # hero: the box is the full viewport width and HERO_HEIGHTS tall
    parts, low = [], 0
    for high, height in HERO_HEIGHTS:
        need = height * ar * m
        if high is None:
            if need > low:
                parts.append("(max-width: %s) %s" % (px(need), px(need)))
            parts.append("100vw")
            break
        parts.append("(max-width: %dpx) %s" % (high, px(max(need, high)) if need > low else "100vw"))
        low = high
    # drop a "100vw" entry when the next one says the same
    out = []
    for i, p in enumerate(parts):
        nxt = parts[i + 1] if i + 1 < len(parts) else None
        if nxt is not None and p.endswith(" 100vw") and nxt.endswith("100vw"):
            continue
        out.append(p)
    return ", ".join(out)


def slot_kind(img):
    figure = next((a for a in reversed(img.ancestors) if a.name == "figure"), None)
    if figure is None or "slot" not in figure.cls():
        return None, None
    if figure.attrs.get("data-photo") == "hero" or any(a.name == "section" and "hero" in a.cls() for a in img.ancestors):
        return figure, "hero"
    if any("card" in a.cls() for a in img.ancestors):
        return figure, "card"
    if "tall" in figure.cls():
        return figure, "tall"
    return figure, "unknown"


def process_photos(page, src_dir, out_dir):
    """Make the smaller copies and return the page with srcset/sizes (and the hero <picture>)."""
    edits = []
    for img in Scanner(page).tags:
        if img.name != "img":
            continue
        figure, kind = slot_kind(img)
        if figure is None:
            continue
        name = figure.attrs.get("data-photo") or img.attrs.get("src") or "?"
        src = img.attrs.get("src") or ""
        if kind == "unknown":
            warn("slot '%s' is not a hero, card or tall slot; its photo is published unchanged" % name)
            continue
        if "srcset" in img.attrs:
            warn("slot '%s' already has srcset; left as it is" % name)
            continue
        if not is_relative(src):
            warn("slot '%s': photo '%s' is not a file in docs/; left as it is" % (name, src))
            continue
        path = os.path.join(src_dir, *src.split("?")[0].split("/"))
        if not os.path.isfile(path):
            warn("slot '%s': %s does not exist; left as it is" % (name, src))
            continue
        try:
            edits.append(resize_one(page, img, kind, src, path, out_dir, src_dir))
        except Exception as e:  # a damaged or unusual file must not stop the publish
            warn("slot '%s': could not make smaller copies of %s (%s); left as it is" % (name, src, e))
    return apply_edits(page, [e for e in edits if e])


def resize_one(page, img, kind, src, path, out_dir, src_dir):
    with Image.open(path) as original:
        if original.format != "JPEG":
            warn("%s is %s, not JPEG; left as it is" % (src, original.format))
            return None
        icc = original.info.get("icc_profile")
        quality = min(jpeg_quality(original), MAX_QUALITY)
        sampling = {0: "4:4:4", 1: "4:2:2", 2: "4:2:0"}.get(JpegImagePlugin.get_sampling(original), "4:2:0")
        rotated = (original.getexif() or {}).get(0x0112, 1) not in (None, 1)
        im = ImageOps.exif_transpose(original)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        width, height = im.size
        ar = width / height
        folder, file = os.path.split(src)
        stem = os.path.splitext(file)[0]
        rel_dir = folder + "/" if folder else ""
        out_folder = os.path.join(out_dir, *folder.split("/")) if folder else out_dir

        candidates = []
        for w in WIDTHS:
            if w >= width:
                break
            h = round(height * w / width)
            name = "%s-%dw.jpg" % (stem, w)
            save_jpeg(im.resize((w, h), Image.LANCZOS), os.path.join(out_folder, name), icc,
                      quality=quality, subsampling=sampling)
            candidates.append((rel_dir + name, w))
        if not candidates:
            print("  %s: %dpx wide, no smaller copies needed" % (src, width))
            return None
        candidates.append((src, width))
        srcset = ", ".join("%s %dw" % c for c in candidates)
        sizes = sizes_for(kind, ar)
        tag = set_attr(set_attr(page[img.start:img.end], "srcset", srcset), "sizes", sizes)
        print("  %s (%s, %dx%d): %s" % (src, kind, width, height, ", ".join(str(w) for _, w in candidates)))
        print("      sizes=\"%s\"" % sizes)

        if kind == "hero" and HERO_PHONE_MAX and ar > HERO_PHONE_ASPECT:
            # Centre crop, cut on the 16px JPEG block grid and saved with the original's quantisation tables,
            # so the phone sees the same pixels as before from a smaller file.
            crop_w = min(width, math.ceil(height * HERO_PHONE_ASPECT))
            left = (width - crop_w) // 2 // 16 * 16
            crop = im.crop((left, 0, width - left, height))
            name = "%s-phone.jpg" % stem
            if rotated or not getattr(original, "quantization", None):
                save_jpeg(crop, os.path.join(out_folder, name), icc, quality=quality, subsampling=sampling)
            else:
                save_jpeg(crop, os.path.join(out_folder, name), icc, qtables=original.quantization, subsampling=sampling)
            source = '<source media="(max-width: %dpx)" srcset="%s">' % (HERO_PHONE_MAX, html.escape(rel_dir + name))
            print("      phones up to %dpx: %s (%dx%d)" % (HERO_PHONE_MAX, rel_dir + name, crop.width, crop.height))
            tag = "<picture>" + source + tag + "</picture>"
        return (img.start, img.end, tag)


# ---------------------------------------------------------------- language pages

def lang_links(text, own_url):
    """hreflang alternates for both pages, placed after the canonical link."""
    links = ('<link rel="alternate" hreflang="mn" href="%s">\n'
             '<link rel="alternate" hreflang="en" href="%s%s/">\n'
             '<link rel="alternate" hreflang="x-default" href="%s">' % (SITE, SITE, EN_DIR, SITE))
    m = re.search(r'<link\s[^>]*rel="canonical"[^>]*>', text)
    if m:
        return text[:m.end()] + "\n" + links + text[m.end():]
    warn("no canonical link found; hreflang links added before </head>")
    return text.replace("</head>", links + "\n</head>", 1)


# Runs in <head> before anything is drawn: old ?lang=xx / #xx links and a saved MN/EN choice go to the
# right address. The English page only follows explicit ?lang=mn / #mn links (its address is a choice).
REDIRECT = ("<script>(function(){try{var p=new URLSearchParams(location.search),q=p.get('lang'),h=location.hash,s=null;"
            "if(!q&&/^#(en|mn)$/.test(h))q=h.slice(1);%s"
            "if(q===%s){p.delete('lang');p=p.toString();"
            "location.replace(%s+(p?'?'+p:'')+(/^#(en|mn)$/.test(h)?'':h));}}catch(e){}})();</script>")
# A saved English choice applies to visits from outside the site, not to Back/Forward (a page reloaded from
# history would bounce straight back to /en/) or to the Mongolian page opened from our own link.
REDIRECT_MN = REDIRECT % ("try{s=localStorage.getItem('mhs-lang')}catch(e){}"
                          "var n=performance.getEntriesByType('navigation')[0];"
                          "if(!q&&s==='en'&&!(n&&n.type==='back_forward')&&document.referrer.indexOf(location.origin+'/')!==0)q='en';",
                          "'en'", "'%s/'" % EN_DIR)
REDIRECT_EN = REDIRECT % ("", "'mn'", "'../'")


def add_head_script(text, script):
    m = re.search(r'<meta\s[^>]*name="viewport"[^>]*>', text) or re.search(r"<meta\s+charset[^>]*>", text)
    if not m:
        warn("no viewport/charset meta; language redirect script put at the start of <head>")
        m = re.search(r"<head[^>]*>", text)
    return text[:m.end()] + "\n" + script + text[m.end():]


def lang_buttons(text, hrefs, pressed):
    edits = []
    for tag in Scanner(text).tags:
        lang = tag.attrs.get("data-set-lang")
        if lang in hrefs:
            t = set_attr(text[tag.start:tag.end], "data-href", hrefs[lang])
            t = set_attr(t, "aria-pressed", "true" if lang == pressed else "false")
            edits.append((tag.start, tag.end, t))
    if len(edits) != 2:
        warn("expected two language buttons, found %d" % len(edits))
    return apply_edits(text, edits)


def set_meta(text, attr, key, value, label):
    pattern = re.compile(r'<meta\s[^>]*%s="%s"[^>]*>' % (attr, re.escape(key)))
    m = pattern.search(text)
    if not m:
        warn("%s not found; not set on the English page" % label)
        return text
    return text[:m.start()] + set_attr(m.group(0), "content", value) + text[m.end():]


def set_link_href(text, rel, value, label):
    m = re.search(r'<link\s[^>]*rel="%s"[^>]*>' % rel, text)
    if not m:
        warn("%s not found; not set on the English page" % label)
        return text
    return text[:m.start()] + set_attr(m.group(0), "href", value) + text[m.end():]


def up_one(url):
    return "../" + url if is_relative(url) else url


def make_english(page, src_dir):
    """The English page: same HTML with English as the default language, served from /en/."""
    tags = Scanner(page).tags
    site = next((t for t in tags if "site" in t.cls() and "data-lang" in t.attrs), None)
    if site is None:
        raise ValueError("no .site element with data-lang")
    edits = []
    title_en = site.attrs.get("data-title-en")

    for t in tags:
        raw = page[t.start:t.end]
        new = raw
        if t.name == "html":
            new = set_attr(new, "lang", "en")
        if t is site:
            new = set_attr(new, "data-lang", "en")
        for data, attr in (("data-alt-en", "alt"), ("data-ph-en", "placeholder"), ("data-aria-en", "aria-label")):
            if data in t.attrs:
                new = set_attr(new, attr, t.attrs[data])
        # relative addresses move one folder up
        for attr in ("src", "href"):
            value = t.attrs.get(attr)
            if value and is_relative(value):
                new = set_attr(new, attr, up_one(value))
        if t.attrs.get("srcset"):
            parts = [p.strip().split(None, 1) for p in t.attrs["srcset"].split(",") if p.strip()]
            new = set_attr(new, "srcset", ", ".join(" ".join([up_one(p[0])] + p[1:]) for p in parts))
        if t.attrs.get("style") and "url(" in t.attrs["style"]:
            new = set_attr(new, "style", css_up(t.attrs["style"]))
        if new != raw:
            edits.append((t.start, t.end, new))
    page = apply_edits(page, edits)

    # url(...) inside <style>
    page = re.sub(r"(<style[^>]*>)(.*?)(</style>)", lambda m: m.group(1) + css_up(m.group(2)) + m.group(3), page, flags=re.S)

    # preload the latin fonts instead of the cyrillic ones
    def latin_preload(m):
        tag = m.group(0)
        href = re.search(r'href="([^"]*)"', tag).group(1)
        swapped = href.replace("-cyrillic-", "-latin-")
        local = os.path.join(src_dir, *swapped.replace("../", "", 1).split("/"))
        if swapped != href and os.path.isfile(local):
            return tag.replace(href, swapped)
        return tag
    page = re.sub(r'<link\s[^>]*rel="preload"[^>]*as="font"[^>]*>', latin_preload, page)

    # title and link preview
    if title_en:
        page, n = re.subn(r"<title>.*?</title>", "<title>%s</title>" % html.escape(title_en, quote=False), page, count=1, flags=re.S)
        if not n:
            warn("no <title> found")
        page = set_meta(page, "property", "og:title", title_en, "og:title")
    else:
        warn("no data-title-en on .site; the English page keeps the Mongolian title")

    description = english_description(page)
    if description:
        page = set_meta(page, "name", "description", description, "meta description")
        page = set_meta(page, "property", "og:description", description, "og:description")
    page = set_meta(page, "property", "og:locale", "en_US", "og:locale")
    page = set_meta(page, "property", "og:locale:alternate", "mn_MN", "og:locale:alternate")
    page = set_meta(page, "property", "og:url", SITE + EN_DIR + "/", "og:url")
    page = set_link_href(page, "canonical", SITE + EN_DIR + "/", "canonical link")
    hero_alt = english_hero_alt(page)
    if hero_alt:
        page = set_meta(page, "property", "og:image:alt", hero_alt, "og:image:alt")
    return page


def css_up(css):
    return re.sub(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", lambda m: "url(%s%s%s)" % (m.group(1), up_one(m.group(2)), m.group(1)), css)


def english_description(page):
    """The English text of the hero's lead paragraph (the page's own summary)."""
    tags = Scanner(page).tags
    for t in tags:
        if t.name == "span" and t.attrs.get("lang") == "en" and any(a.name == "p" and "lead" in a.cls() for a in t.ancestors):
            text = inner_text(page, t)
            if text:
                return text
    warn("no English lead paragraph (.lead span[lang=en]) found; the English page keeps the Mongolian description")
    return None


def english_hero_alt(page):
    for t in Scanner(page).tags:
        if t.name == "img" and t.attrs.get("data-alt-en") and any(a.attrs.get("data-photo") == "hero" for a in t.ancestors):
            alt = t.attrs["data-alt-en"]
            return alt[:1].upper() + alt[1:]
    return None


# ---------------------------------------------------------------- main

def build(src_dir, out_dir):
    # The output folder is deleted first, so it must never be the source, inside it, or contain it.
    src_real = os.path.normcase(os.path.realpath(src_dir))
    out_real = os.path.normcase(os.path.realpath(out_dir))
    if os.path.commonpath([src_real, out_real]) in (src_real, out_real):
        print("ERROR: output folder %s overlaps source folder %s (same folder, or one inside the other); "
              "nothing was built or deleted. Use a separate output folder, e.g. _site." % (out_dir, src_dir),
              file=sys.stderr)
        sys.exit(2)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    shutil.copytree(src_dir, out_dir)
    index = os.path.join(src_dir, "index.html")
    if not os.path.isfile(index):
        warn("%s not found; published the folder as it is" % index)
        return
    with open(index, encoding="utf-8") as f:
        source = f.read()

    try:
        print("Photos:")
        page = process_photos(source, src_dir, out_dir)
    except Exception as e:
        warn("photo step failed (%s: %s); photos published without smaller copies" % (type(e).__name__, e))
        page = source

    try:
        english = make_english(page, src_dir)
        english = lang_links(english, SITE + EN_DIR + "/")
        english = add_head_script(english, REDIRECT_EN)
        english = lang_buttons(english, {"mn": "../", "en": "./"}, "en")
        mongolian = lang_links(page, SITE)
        mongolian = add_head_script(mongolian, REDIRECT_MN)
        mongolian = lang_buttons(mongolian, {"mn": "./", "en": EN_DIR + "/"}, "mn")
    except Exception as e:
        warn("English page not built (%s: %s); the site is published with the in-page language switch only" % (type(e).__name__, e))
        english, mongolian = None, page

    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(mongolian)
    if english is not None:
        os.makedirs(os.path.join(out_dir, EN_DIR), exist_ok=True)
        with open(os.path.join(out_dir, EN_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write(english)
        print("English page: %s/index.html" % EN_DIR)


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "docs"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "_site"
    build(src_dir, out_dir)
    print("Built %s from %s with %d warning(s)." % (out_dir, src_dir, len(warnings)))


if __name__ == "__main__":
    main()
