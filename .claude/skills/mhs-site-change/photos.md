# Photos for mhs.mn

CLAUDE.md says what a published photo may not show. This page explains how a photo gets from the owner's camera roll into `docs/photos/`. The steps come from 28 Nov 2026, when about thirty of his photos went in.

## 1. Find and fetch

- **Where they are:** his photos are in his OneDrive camera rolls, which are connected to sessions as folders (`get_device_info` lists them). Sometimes he attaches them in the chat. He refers to them by file number (N206, W0864) or by machine.
- **Fetching:** list the folder with `device_list_dir`, then stage only the photos the task needs with `device_stage_files`. Most are cloud-only (`cloudOnly`), and he can't make all photos available on his PC. Write into those folders only with his permission (owner, 28 Nov 2026).
- **Choosing:** look at each candidate (Read the staged file) before choosing. When he names a photo, use that one.

## 2. Check what it shows

Look at each photo at full size, region by region (crop it and Read the crop). Look for:

- painted company or mine names and logos on machine bodies, canopies and crates;
- licence plates;
- other fire-suppression makers' names, such as a label on a nitrogen cartridge;
- people other than the MHS crew.

Small labels are easy to miss.

## 3. Paint over what must go

```bash
python3 .claude/skills/mhs-site-change/photo_prep.py blank SRC OUT.jpg --box X0,Y0,X1,Y1 [--box …] [--fill lr|tb|all]
```

- **Coordinates:** they are pixels of the upright photo. Find them on a crop first.
- **Box size:** the box must cover the thing completely on the sides it fills from (`lr`, the default, fills from left and right). For a plate whose letters reach its top and bottom, keep the box inside the plate left and right.
- **What it can handle:** plain surfaces such as plates, painted panels and labels on metal. Patterns such as tyre tread or grilles don't work: crop those out, or choose another photo.
- **Checking:** look at the result at full size. If a smear or a seam shows, move the box and run it again.

## 4. Crop, size and strip

```bash
python3 .claude/skills/mhs-site-change/photo_prep.py prep SRC docs/photos/NAME.jpg [--crop 4:3] [--focus CX,CY] [--zoom Z] [--width W]
python3 .claude/skills/mhs-site-change/photo_prep.py check
```

- **Width:** the hero is 2000 px. Cards, the crew photo and the big «Манай суурилуулалтаас» tiles are 1600. Track-record tiles, steps and close-ups are 1200.
- **Crop:**
  - 4:3 is the default, for track-record tiles, steps and close-ups;
  - cards keep their own shape (`--crop 16:10` for the team card);
  - `--focus` moves the crop window and `--zoom` tightens it;
  - a pixel box works too.
- **No EXIF:** `prep` writes none, so GPS and camera data are gone (iPhone photos carry the mine's coordinates).
- **Checking the folder:** `check` lists photos in `docs/photos/` that still have EXIF, are wider than 2000 px or are build copies.

## 5. Name and place

- **File names** say what the photo is: `hero-…`, `card-…`, `step-N-…`, `model-<make>-<model>.jpg` (track record), `part-…` (installed parts) and `crew-…`. The owner can replace a photo later by uploading a file with the same name.
- **In the page,** each photo sits in a `<figure class="slot KIND">`. Give it `width` and `height`, `loading="lazy"` below the first screen, and `data-alt-mn/en/zh`. Alt text names no customers either.
- **New slot kind:** it needs its box in `BOXES` (see CLAUDE.md, "Photo boxes").
- **New hero photo:** it needs a new `docs/og-image.jpg` (1200×630, cropped from the hero).
- **Review:** photos go to the owner for review before the merge question (SKILL.md, step 4).
