#!/usr/bin/env python3
"""Prepare a Cloudflare Pages upload of mhs.mn that the owner's browser can assemble itself.

Why: the cloud shell can't reach mhs.mn, and the browser can't read files from the cloud shell. But the
browser can fetch every unchanged file from the live site. So we send it only the *differences*.

Usage:
    python3 cf_prepare.py OLD_SITE NEW_SITE > /tmp/cf_plan.json

OLD_SITE  a build of what is live now (normally: build origin/main into a separate folder; first confirm
          with cf_deploy.md step 1 that the live pages match it).
NEW_SITE  your new build (_site), which must already contain 404.html and _headers (the build copies them
          from docs/).

Output JSON:
    sha      {path: first 16 hex of sha256} for every file in NEW_SITE — the browser checks each file against it
    patches  {path: [[start, end, text], ...]} for changed UTF-8 text files: edit operations on the live file
    new      [path, ...] files that are new or changed binary files (photos!). The browser can't make these:
             see cf_deploy.md, "New or changed photos".
"""
import difflib
import hashlib
import json
import os
import sys


def files(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")
            out[p] = open(os.path.join(d, f), "rb").read()
    return out


def main(old_root, new_root):
    old, new = files(old_root), files(new_root)
    plan = {"sha": {}, "patches": {}, "new": []}
    for p, b in sorted(new.items()):
        plan["sha"][p] = hashlib.sha256(b).hexdigest()[:16]
        if old.get(p) == b:
            continue
        try:
            a_txt, b_txt = old[p].decode("utf-8"), b.decode("utf-8")
            # JS strings index by UTF-16 units; positions only agree when there are no astral characters
            if any(ord(c) > 0xFFFF for c in a_txt + b_txt):
                raise ValueError("astral characters")
        except (KeyError, UnicodeDecodeError, ValueError):
            plan["new"].append(p)
            continue
        ops = [[i1, i2, b_txt[j1:j2]]
               for t, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a_txt, b_txt, autojunk=False).get_opcodes()
               if t != "equal"]
        s = a_txt
        for i1, i2, t in reversed(ops):
            s = s[:i1] + t + s[i2:]
        assert s == b_txt, p
        plan["patches"][p] = ops
    json.dump(plan, sys.stdout, ensure_ascii=False, separators=(",", ":"))
    print("\n%d files, %d patched, %d new/binary: %s" % (len(new), len(plan["patches"]), len(plan["new"]),
          ", ".join(plan["new"]) or "none"), file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
