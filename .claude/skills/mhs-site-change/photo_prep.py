#!/usr/bin/env python3
"""Prepare the owner's photos for docs/photos/ (Pillow and numpy only; see photos.md).

  prep  SRC OUT [--crop 4:3|16:10|X0,Y0,X1,Y1|none] [--focus CX,CY] [--zoom Z] [--width W] [--quality Q]
  blank SRC OUT --box X0,Y0,X1,Y1 [--box ...] [--fill lr|tb|all] [--texture X0,Y0,X1,Y1]
  check [DIR]

prep   Turns the photo upright (EXIF orientation), crops it (4:3 and centred by default; --focus
       0..1 moves the window, --zoom above 1 tightens it), scales it down to --width px (default
       1200) and saves a progressive JPEG (quality 82) with no EXIF, so GPS and camera data are gone.
blank  Paints over painted names, logos, licence plates or labels. Each box (pixels of the upright
       photo) is filled from the pixels just outside it: each row from its left and right ends
       (--fill lr, the default), each column from above and below (tb), or both blended (all).
       Grain as strong as the surroundings' is added (or real texture from --texture, a plain
       sample area you pick), and the edges are soft. The box must cover the thing completely on
       the sides it fills from, or the thing smears back in: for a plate whose letters reach its
       top and bottom, keep the box inside the plate left and right and use lr. It works on plain
       surfaces (plates, painted panels, labels on metal), not on patterns such as tyre tread or
       grilles: crop those out instead. Always look at the result at full size.
check  Lists photos in DIR (default docs/photos) that carry EXIF/GPS, are wider than 2000 px, or are
       build copies (-800w, -phone) that must not be committed. Exit code 1 if any.
"""
import argparse
import pathlib
import sys

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def load(path):
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def parse_box(text):
    vals = [int(round(float(v))) for v in text.split(",")]
    if len(vals) != 4 or vals[2] <= vals[0] or vals[3] <= vals[1]:
        raise argparse.ArgumentTypeError("a box is X0,Y0,X1,Y1 with X1>X0 and Y1>Y0")
    return vals


def crop_ratio(im, rw, rh, cx=0.5, cy=0.5, zoom=1.0):
    w, h = im.size
    tw = w / zoom
    th = tw * rh / rw
    if th > h / zoom:
        th = h / zoom
        tw = th * rw / rh
    left = min(max(cx * w - tw / 2, 0), w - tw)
    top = min(max(cy * h - th / 2, 0), h - th)
    return im.crop((round(left), round(top), round(left + tw), round(top + th)))


def save(im, out, quality):
    out = pathlib.Path(out)
    if out.suffix.lower() in (".jpg", ".jpeg"):
        im.save(out, quality=quality, optimize=True, progressive=True)  # no exif= : stripped
    else:
        im.save(out)
    print(f"{out.name}: {im.width}x{im.height}, {out.stat().st_size // 1024} KB")


def cmd_prep(a):
    im = load(a.src)
    crop = a.crop.lower()
    if crop == "none":
        pass
    elif ":" in crop:
        rw, rh = (float(v) for v in crop.split(":"))
        cx, cy = (float(v) for v in a.focus.split(","))
        im = crop_ratio(im, rw, rh, cx, cy, a.zoom)
    else:
        im = im.crop(tuple(parse_box(crop)))
    if im.width > a.width:
        im = im.resize((a.width, round(im.height * a.width / im.width)), Image.LANCZOS)
    save(im, a.out, a.quality)


def smooth_rows(a, sigma=4.0):
    """Gaussian smoothing of an (h, 3) array along its rows."""
    r = max(1, int(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    padded = np.pad(a, ((r, r), (0, 0)), mode="edge")
    return np.stack([np.convolve(padded[:, c], k, mode="valid") for c in range(a.shape[1])], -1)


def high_pass(region_u8, sigma=4.0):
    img = Image.fromarray(region_u8)
    low = np.asarray(img.filter(ImageFilter.GaussianBlur(sigma)), dtype=float)
    return region_u8.astype(float) - low


def cmd_blank(a):
    im = load(a.src)
    arr = np.asarray(im, dtype=float).copy()
    src_u8 = np.asarray(im)
    H, W = arr.shape[:2]
    rng = np.random.default_rng(7)
    for x0, y0, x1, y1 in a.box:
        x0, x1 = max(0, x0), min(W, x1)
        y0, y1 = max(0, y0), min(H, y1)
        w, h = x1 - x0, y1 - y0
        if w < 4 or h < 4:
            sys.exit(f"box {x0},{y0},{x1},{y1} is too small or outside the photo ({W}x{H})")
        # smooth fill from the pixels just outside the box: each row from its left and right ends
        # (lr), each column from above and below (tb), or both blended (all)
        u = np.linspace(0, 1, w)[None, :, None]
        v = np.linspace(0, 1, h)[:, None, None]
        have_lr, have_tb = x0 >= 3 and x1 <= W - 3, y0 >= 3 and y1 <= H - 3
        mode = a.fill
        if mode in ("lr", "all") and not have_lr:
            mode = "tb"
        if mode in ("tb", "all") and not have_tb:
            mode = "lr" if have_lr else None
        if mode is None:
            sys.exit(f"box {x0},{y0},{x1},{y1} has no surroundings to fill from")
        if mode in ("lr", "all"):
            left = smooth_rows(arr[y0:y1, x0 - 3:x0].mean(1))
            right = smooth_rows(arr[y0:y1, x1:x1 + 3].mean(1))
            horiz = left[:, None, :] * (1 - u) + right[:, None, :] * u
        if mode in ("tb", "all"):
            top = smooth_rows(arr[y0 - 3:y0, x0:x1].mean(0))
            bottom = smooth_rows(arr[y1:y1 + 3, x0:x1].mean(0))
            vert = top[None, :, :] * (1 - v) + bottom[None, :, :] * v
        fill = horiz if mode == "lr" else vert if mode == "tb" else (horiz + vert) / 2
        if a.texture:  # real texture from a plain sample area the user picked
            tx0, ty0, tx1, ty1 = a.texture
            tex = np.clip(high_pass(src_u8[ty0:ty1, tx0:tx1]), -10, 10)  # grain only, no edges
            reps = (int(np.ceil(h / tex.shape[0])), int(np.ceil(w / tex.shape[1])), 1)
            fill = fill + np.tile(tex, reps)[:h, :w] * 0.8
        else:  # grain as strong as in a ring just outside the box (borrowed texture leaves ghosts)
            ex0, ey0, ex1, ey1 = max(0, x0 - 8), max(0, y0 - 8), min(W, x1 + 8), min(H, y1 + 8)
            hp = np.clip(high_pass(src_u8[ey0:ey1, ex0:ex1]), -10, 10)
            ring = np.ones(hp.shape[:2], bool)
            ring[y0 - ey0:y1 - ey0, x0 - ex0:x1 - ex0] = False
            lum = hp[ring].mean(-1) if ring.any() else np.zeros(1)
            grain = float(np.clip(1.4826 * np.median(np.abs(lum - np.median(lum))), 0.8, 4.0))
            noise = rng.normal(0, 1, (h + 4, w + 4))
            k = np.exp(-0.5 * (np.arange(-2, 3) / 0.7) ** 2)
            k /= k.sum()
            noise = np.apply_along_axis(lambda r: np.convolve(r, k, mode="valid"), 1, noise)
            noise = np.apply_along_axis(lambda c: np.convolve(c, k, mode="valid"), 0, noise)
            fill = fill + (noise / noise.std() * grain)[..., None]
        mask = Image.new("L", (w, h), 0)
        mask.paste(255, (5, 5, max(6, w - 5), max(6, h - 5)))
        m = np.clip(np.asarray(mask.filter(ImageFilter.GaussianBlur(2.5)), dtype=float) / 255 * 1.3, 0, 1)
        arr[y0:y1, x0:x1] = arr[y0:y1, x0:x1] * (1 - m[..., None]) + fill * m[..., None]
    out = Image.fromarray(np.clip(arr, 0, 255).round().astype(np.uint8))
    if pathlib.Path(a.out).suffix.lower() in (".jpg", ".jpeg"):
        out.save(a.out, quality=93, subsampling=0)
    else:
        out.save(a.out)
    print(f"{pathlib.Path(a.out).name}: {len(a.box)} area(s) painted over; look at it at full size")


def cmd_check(a):
    problems = []
    for p in sorted(pathlib.Path(a.dir).iterdir()):
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        if "-800w" in p.stem or p.stem.endswith("-phone"):
            problems.append(f"{p.name}: build copy, must not be committed")
        with Image.open(p) as im:
            exif = im.getexif()
            if len(exif) or "exif" in im.info:
                gps = " with GPS" if 0x8825 in exif else ""
                problems.append(f"{p.name}: has EXIF{gps}")
            if im.width > 2000:
                problems.append(f"{p.name}: {im.width} px wide (keep 2000 or less)")
    print("\n".join(problems) or f"{a.dir}: no EXIF, nothing wider than 2000 px, no build copies")
    sys.exit(1 if problems else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("src")
    p.add_argument("out")
    p.add_argument("--crop", default="4:3")
    p.add_argument("--focus", default="0.5,0.5")
    p.add_argument("--zoom", type=float, default=1.0)
    p.add_argument("--width", type=int, default=1200)
    p.add_argument("--quality", type=int, default=82)
    b = sub.add_parser("blank")
    b.add_argument("src")
    b.add_argument("out")
    b.add_argument("--box", type=parse_box, action="append", required=True)
    b.add_argument("--texture", type=parse_box)
    b.add_argument("--fill", choices=("lr", "tb", "all"), default="lr")
    c = sub.add_parser("check")
    c.add_argument("dir", nargs="?", default="docs/photos")
    a = ap.parse_args()
    {"prep": cmd_prep, "blank": cmd_blank, "check": cmd_check}[a.cmd](a)


if __name__ == "__main__":
    main()
