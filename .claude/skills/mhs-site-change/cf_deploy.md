# Publishing mhs.mn to Cloudflare Pages

Since 7 Nov 2026, mhs.mn is served by Cloudflare Pages: project `mhs-mn`, account id `11367a073bab02e5947460e024a4dc6b`, **direct upload** (no Git connection). A merge to `main` publishes nothing. This page explains how to publish. The method was first used on 26 Nov 2026.

## What can reach what

- **The cloud shell** can't open mhs.mn and can't reach the Cloudflare API with the owner's sign-in.
- **The owner's browser** (built-in browser or Claude in Chrome) can fetch from mhs.mn and work in the Cloudflare dashboard once the owner has signed in. He signs in himself; never type credentials. Cloudflare is often signed out, so ask him to sign in first.
- **Claude in Chrome's `file_upload`** only accepts files the owner has shared with the session. Container paths (`/mnt/user-data/outputs/…`) are refused, and a request for device folder access may also be refused.
- **The Pages API from the dashboard page:** `fetch('/api/v4/accounts/<acc>/pages/projects/mhs-mn/upload-token', {headers: {'x-atok': window.bootstrap.atok, 'x-cross-site-security': 'dash'}})` works, as do `/api/v4/pages/assets/check-missing`, `/upload` and `/upsert-hashes` with `Authorization: Bearer <jwt>`. But **a multipart POST to `.../deployments` is blocked** by Cloudflare's WAF ("Attention Required", 403). **Don't create deployments through the API.** Use the dashboard's own upload box (step 4).

## 1. Before you start: is the repo the same as the live site?

Build `origin/main` into a separate folder, then fetch `/`, `/en/`, `/zh/`, `/llms.txt` and `/sitemap.xml` from an mhs.mn tab in the browser and compare their sha256 values with the build:

```js
const sha=async b=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b))).map(x=>x.toString(16).padStart(2,'0')).join('').slice(0,16);
const out={}; for (const p of ['','en/','zh/','llms.txt','sitemap.xml']) { const r=await fetch('/'+p,{cache:'no-store'}); out[p||'/']=await sha(await r.arrayBuffer()); } JSON.stringify(out)
```

If they differ, someone deployed without merging. Ask the owner, and don't overwrite the live site blindly.

## 2. Build and plan

```bash
git worktree add /tmp/base origin/main && python3 /tmp/base/tools/build_site.py /tmp/base/docs /tmp/base/_site   # what is live
rm -rf _site && python3 tools/build_site.py docs _site                                                          # your change
python3 .claude/skills/mhs-site-change/cf_prepare.py /tmp/base/_site _site > /tmp/cf_plan.json   # 2–4 min: run it in the background
```

`_site` must contain `404.html` and `_headers`; the build copies them from `docs/`. The plan file holds:

- a checksum for every file;
- small edit operations for each changed text file;
- a list `new` of new or changed binary files.

## 3. Assemble the files in the browser

Run this in a tab on the Cloudflare dashboard, on the mhs-mn **Create deployment** page (`/pages/view/mhs-mn/deployments/new`), with `PLAN` pasted from `/tmp/cf_plan.json`. It works there because mhs.mn sends `access-control-allow-origin: *`.

```js
const PLAN = /* paste /tmp/cf_plan.json */;
const sha=async b=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b))).map(x=>x.toString(16).padStart(2,'0')).join('').slice(0,16);
const files={}, bad=[];
for (const p of Object.keys(PLAN.sha)) {
  if (PLAN.new.includes(p)) { bad.push('NEW '+p); continue; }
  const r=await fetch('https://mhs.mn/'+p,{cache:'no-store'});
  let u8=new Uint8Array(await r.arrayBuffer());
  if (PLAN.patches[p]) { let s=new TextDecoder().decode(u8); for (const [i1,i2,t] of [...PLAN.patches[p]].reverse()) s=s.slice(0,i1)+t+s.slice(i2); u8=new TextEncoder().encode(s); }
  if (await sha(u8)!==PLAN.sha[p]) bad.push(p);
  files[p]=u8;
}
window.__files=files; JSON.stringify({n:Object.keys(files).length, bad})
```

Don't go on unless `bad` is empty. A path that doesn't exist on the live site yet, such as `_headers`, comes back as a 404 page and shows up in `bad`. Add such small text files by hand, as `files[p]=new TextEncoder().encode('…')`.

**New or changed photos** can't be made this way. Choose one:

- Ask the owner to share a folder with the session, then use Chrome's `file_upload`.
- Ask the owner to upload the zip (`_site` zipped) himself in the same dashboard box.

## 4. Zip in the page and hand it to the upload box

```js
const T=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;T[n]=c>>>0}
const crc=u=>{let c=0xFFFFFFFF;for(let i=0;i<u.length;i++)c=T[(c^u[i])&255]^(c>>>8);return (c^0xFFFFFFFF)>>>0};
const parts=[],central=[];let off=0;const enc=new TextEncoder();
for(const [name,data] of Object.entries(window.__files)){const nb=enc.encode(name),c=crc(data);
 const lh=new DataView(new ArrayBuffer(30));lh.setUint32(0,0x04034b50,true);lh.setUint16(4,20,true);lh.setUint16(6,0x0800,true);lh.setUint16(12,0x5821,true);lh.setUint32(14,c,true);lh.setUint32(18,data.length,true);lh.setUint32(22,data.length,true);lh.setUint16(26,nb.length,true);
 parts.push(new Uint8Array(lh.buffer),nb,data);
 const ch=new DataView(new ArrayBuffer(46));ch.setUint32(0,0x02014b50,true);ch.setUint16(4,20,true);ch.setUint16(6,20,true);ch.setUint16(8,0x0800,true);ch.setUint16(14,0x5821,true);ch.setUint32(16,c,true);ch.setUint32(20,data.length,true);ch.setUint32(24,data.length,true);ch.setUint16(28,nb.length,true);ch.setUint32(42,off,true);
 central.push(new Uint8Array(ch.buffer),nb); off+=30+nb.length+data.length;}
const cd=central.reduce((a,b)=>a+b.length,0),e=new DataView(new ArrayBuffer(22)),n=Object.keys(window.__files).length;
e.setUint32(0,0x06054b50,true);e.setUint16(8,n,true);e.setUint16(10,n,true);e.setUint32(12,cd,true);e.setUint32(16,off,true);
const zip=new File([...parts,...central,new Uint8Array(e.buffer)],'mhs-site.zip',{type:'application/zip'});
const i=document.querySelector('input[type=file][accept=".zip"]'); const dt=new DataTransfer(); dt.items.add(zip); i.files=dt.files;
i.dispatchEvent(new Event('change',{bubbles:true})); zip.size
```

Then:

1. The page should say "N/N files uploaded". Check that it does.
2. Check that **Production** is selected.
3. Click **Save and deploy**, and wait for the "Success!" page.

## 5. Check the live site

1. From an mhs.mn tab, run step 1's snippet against your new build's checksums. Every one must match.
2. Check that `/nope` returns 404 with «Хуудас олдсонгүй».
3. Check that `fetch('/')` on mhs-mn.pages.dev has `x-robots-tag: noindex` and mhs.mn has none.
4. Ping IndexNow from a bing.com tab: `fetch('/indexnow?url='+encodeURIComponent(u)+'&key=ef8d0dd29fefc4380d8930910c1606e7')` for `/`, `/en/`, `/zh/` and `/llms.txt`.

## 6. Merge

Commit, open the PR, and merge to `main` in the same session, following the merge rule in CLAUDE.md, so the repo stays equal to the live site. Close the browser tabs you opened.
