# Glowberry — project brief

Canonical brief for concept, fabrication (Studio Artefact), and systems. Budget open. First-wave funder locked 2026-08-26: Canada Council Explore and Create, Artistic Creation.

**Project title:** Glowberry (bakeapple / cloudberry pilgrimage sculpture).

| Companion docs | |
|----------------|--|
| [`RESEARCH_sculpture_precedents.md`](RESEARCH_sculpture_precedents.md) | Sculpture / material precedents |
| [`BIBLIOGRAPHY.md`](BIBLIOGRAPHY.md) | **Living bibliography** — readings, texts, research |
| [`MATERIALS.md`](MATERIALS.md) | Print materials, coatings, translucency, mass bands |
| [`POWER.md`](POWER.md) | Lighting, battery, solar, controller detail |
| [`INFLATABLE.md`](INFLATABLE.md) | **Out** (2026-08-26). Archived notes for a Choi-lineage inflatable; not a live track |
| [`SITE.md`](SITE.md) | NL site longlist (no place chosen; no permissions claimed) |

---

## 1. Concept (locked)

**Glowberry** — monumental ripe bakeapple (cloudberry) as an accessible pilgrimage sculpture.

| | |
|--|--|
| **Tone** | Awe + humor + uncanny presence |
| **Body** | Resettled object — returned / transplanted “soul” (artist in Montreal; work for Newfoundland) |
| **Not** | Weather station, enterable pavilion, data dashboard |
| **Yes** | Beacon fruit people travel to see; soft **heartbeat / breathing glow** |
| **Audience** | Newfoundlanders *and* visitors |
| **Practice lineage** | Continues *Cloudberry* (presence / solar failure), *Light House* (beacon), *Driftwood* / *Adrift* (live systems), bakeapple as reason for return to Pinchard’s |

---

## 2. Interaction & siting (locked)

| | |
|--|--|
| **Allowed** | Touch, sit near, walk around, photograph |
| **Not allowed** | Entering the interior |
| **Site** | TBD. Named list in [`SITE.md`](SITE.md) ([#11](https://github.com/adamsimms/glowberry/issues/11) and [#14](https://github.com/adamsimms/glowberry/issues/14) closed). Ping all for traction after the pitch. Partner-led regions plus named Avalon places (including Quidi Vidi). Signal Hill dropped. Not near Pinchard's. No permissions claimed. |
| **Landscape character** | Inland of shore / rock or cliff plateau; open coastal view |
| **Site mock** | Local moodboard only for now (not in repo); coastal plateau / shore–cliff character |
| **Pedestal** | Not required in art direction (fruit “landed/grown”); fabricator may need hidden anchors |

---

## 3. Material & light (locked)

**Target:** semi-opaque **translucent glowing orange** — light *in the flesh*.

| | |
|--|--|
| **Look** | Saturated amber → vermillion; soft internal luminescence |
| **Build** | Hollow shell + diffusion + internal LEDs + hatch at stem/bottom |
| **Candidates** | Translucent **FRP / fiberglass–resin**; translucent **PETG** (Artefact); light-passing tints/clearcoats — see [`MATERIALS.md`](MATERIALS.md) |
| **Avoid** | Fully opaque paint (kills glow); polished stainless as primary skin |
| **When it glows** | **Dusk / night** is the show — no daytime glow requirement |
| **Behavior** | Simple breathing / heartbeat pulse (ESP32-class MCU) |
| **Darkness** | Outdoor: occasional dark nights **OK** (part of the work) |

---

## 4. Power (locked)

| Scale | Role | Power |
|-------|------|--------|
| **≤ ~60"** (Tiers A & B) | Gallery / indoor or short outdoor loans | **AC plug-in** and/or small **battery pack**; typical **5–8 h** evening run; recharge or plug overnight / closed hours; **no solar** |
| **~10 ft** (Tier C) | Outdoor landmark | **Solar** (panels **hidden** in/under base); **grid assist OK** if site allows; battery for night; dark spells OK |

**Controller:** ESP32 / Arduino / small LED controller — **not** Raspberry Pi (Pi only if a future Cloudberry-style sensing chapter).

Detail + cost bands: [`POWER.md`](POWER.md).

---

## 5. Primary art references

| Reference | Steal | Don’t copy |
|-----------|-------|------------|
| **Yayoi Kusama — Yellow Pumpkin** (Naoshima) | Pilgrimage fruit; island landmark; FRP outdoor fruit; recovery hardware | Opaque paint; polka-dot identity |
| **Paresh Maity — bronze jackfruit** | Monumental fruit as cultural metaphor | Bronze / no glow |
| **Anish Kapoor — Cloud Gate (Chicago Bean)** | Touchable public body; walk-around uncanny scale | Mirror stainless as primary skin |
| **James Turrell — Skyspaces** | Night presence; light as medium; glowing shell logic | Enterable architecture as the work |
| **Leo Villareal — Buckyball** ([Madison Square Park](https://madisonsquarepark.org/art/exhibitions/leo-villareal-buckyball/)) | Light-as-sculpture; public night draw; programmed LED “life” | Open lattice / RGB spectacle; complex generative software |
| **Choi Jeong-hwa — inflatable fruit** | Pop humor; photo magnetism; soft temporary monument | Don’t treat as the permanent NL beacon |

**Stance:** Kusama site + fruit pilgrimage + Turrell/Villareal night light + Kapoor touchability → **translucent FRP/PETG flesh** with a **simple heartbeat**, not a Buckyball-style LED cage.

**Inflatable:** out (2026-08-26). Will not do a Choi-style summer POC. Notes remain in [`INFLATABLE.md`](INFLATABLE.md). Possible process work: smaller test prints of the 3D berry mesh.

---

## 6. Fabrication files (Studio Artefact)

Production mesh package is **not published in this repo yet** (will be added deliberately when quote-ready). Local working files live outside git for now.

When publishing, expect roughly:

| File | Use |
|------|-----|
| `glowberry_master_500mm.stl` | Production mesh (~484k tris) — WeTransfer / Drive |
| `glowberry_master_500mm_preview.stl` | Lighter preview |
| `glowberry_master_500mm.obj` | Alternate format |
| `glowberry.blend` | Blender source (optional) |
| Berry / site refs | Curated references (added intentionally later) |

**Units:** meters; master height **500 mm**. Scale uniformly per tier.

### Geometry

- Drupelets only (no calyx, stem, leaves, hairs)
- Manifold / watertight
- ~447 × 460 × **500 mm**
- **−Z = stem/attachment** (bottom when upright)
- STL uncolored — translucency + LEDs + power are separate scope

### Scale tiers

| Tier | Height | Scale from 500 mm | Role | Fabrication note |
|------|--------|-------------------|------|------------------|
| **Primary (Artefact ask)** | **~6 ft (≈1.8 m)** | **≈3.66×** | Outdoor-capable pilgrimage piece | **First:** Artefact 20 m³ one-piece. **Backup:** 1 m³ split (Artefact or other shops) if one-piece fails or will not fit a 15 ft+ U-Haul door. Translucent PETG ± weather coat |
| A (later) | 20–30" | 1.02×–1.52× | Gallery / study | 1 m³ possible |
| B (later) | 50–60" | 2.54×–3.05× | Gallery | 1 m³ split or 20 m³ |
| C (alt.) | ~7–10 ft | 4.3×–6.1× | Larger landmark | Same family as 6 ft; not the current quote focus |

**Current submission to Artefact:** quote the **~6 ft** piece only. Shop may hollow, rib, thicken walls; advise on translucent outdoor builds.

---

## 7. Contact — Studio Artefact

**Official path:** their [project contact form](https://www.studioartefact.com/en/contact/) (not a free-form cold email alone).

Paste-ready answers + PDF brief: [`docs/artefact/`](artefact/).

Form fields they ask for:

| Field | Suggested for Glowberry |
|-------|-------------------------|
| Project type | **3D printing** |
| Delivery | **In more than six months** (exploratory / grant-dependent) |
| Budget band | **$50,000 or less** for this feasibility ask (or $50–100k if you prefer) |
| Description | Paste from [`artefact/FORM_ANSWERS.md`](artefact/FORM_ANSWERS.md) — **~6 ft only** |
| Documents | PDF from [`artefact/ARTEFACT_SUBMISSION_BRIEF.md`](artefact/ARTEFACT_SUBMISSION_BRIEF.md) + preview image; full STL via WeTransfer |
| How you found them | e.g. online search / recommendation |
| Email / phone | Required |

**Also:** 514-933-7666 · info@studioartefact.com · 7900 av. Blaise-Pascal, Montreal

### Best approach

1. **Submit the form** with the short **6 ft** brief + clear feasibility ask.  
2. After they reply, **co-design** materials, translucent coat, hatch, wall thickness.  
3. Keep the first ask to **feasibility / ballpark range**, not a hard PO.

### Form body (short — ~6 ft)

**Specifically:** Quote / feasibility — Glowberry, translucent glowing bakeapple, **~6 ft**

Hello — Adam Simms, Montreal. Developing **Glowberry** (bakeapple / cloudberry pilgrimage sculpture) with soft internal heartbeat glow. Touchable; walk-around; no entry. NL outdoor site TBD. Funding open — please treat as **feasibility + rough range** for **one size: ~6 ft (≈1.8 m)** tall, scaled from a 500 mm source mesh (≈3.66×). Prefer translucent PETG ± translucent outdoor coat (or FRP if needed); hatch at stem; LEDs may be separate scope. Advise one-piece vs split for a U-Haul 15 ft+ door (7'3" × 6'5") to Newfoundland, cost range, wall/mass, coastal weather finish, timeline. Brief PDF + refs attached; full STL on WeTransfer on request. https://github.com/adamsimms/glowberry — thanks, Adam · hello@adamsimms.xyz · [Phone]

---

## 8. Send checklist

- [ ] Fill [Artefact contact form](https://www.studioartefact.com/en/contact/) (3D printing + timeline + budget band)  
- [ ] Upload **6 ft** PDF brief (+ preview image); WeTransfer full STL if asked  
- [ ] Name / phone / email on form  
- [ ] Stress **translucent / glow-capable** + **~6 ft only**  
- [ ] Ask for **feasibility + range**, not a fixed PO yet  
- [ ] Interaction: touch / sit near / walk around — no entry  

---

## 9. Still open

Working sequence (2026-08-26), in this order:

1. **3D body origin** ([#16](https://github.com/adamsimms/glowberry/issues/16)): keep the modeled ~500 mm mesh, or replace/hybridize via photogrammetry ([#52](https://github.com/adamsimms/glowberry/issues/52)) / other scan spikes ([#51](https://github.com/adamsimms/glowberry/issues/51), [#53](https://github.com/adamsimms/glowberry/issues/53)). Default: modeled mesh is the 6 ft production body until a decision says otherwise.
2. **Test prints** ([#61](https://github.com/adamsimms/glowberry/issues/61)): coupons and/or a small maquette of that mesh.
3. **Quote fabrication** ([#37](https://github.com/adamsimms/glowberry/issues/37)): Artefact 20 m³ one-piece first ([#18](https://github.com/adamsimms/glowberry/issues/18) closed). 1 m³ split is backup. Form still unsent.
4. **Stage / platform** ([#62](https://github.com/adamsimms/glowberry/issues/62)): hidden anchors vs visible furniture. Fruit still reads as landed/grown.
5. **2D maquettes / sketches** ([#17](https://github.com/adamsimms/glowberry/issues/17)): form, person scale, landscape character. Optional render folded in (former #40).
6. **Pitch document in Figma** ([#63](https://github.com/adamsimms/glowberry/issues/63)): also the one-pager. Unblocks site sends ([#34](https://github.com/adamsimms/glowberry/issues/34)).

Also still open:

- Exact NL site + permissions (named list in [`SITE.md`](SITE.md); partner-led regions; map done; no sends until the pitch package)
- Production 3D package for shops (quote-ready mesh; not in this repo yet). Confirm bounding box vs U-Haul door ([`MATERIALS.md`](MATERIALS.md) transport envelope)
- Shell must fit a 15 ft or larger U-Haul door to Newfoundland, or split. See [`MATERIALS.md`](MATERIALS.md)
- Outdoor power: solar-only vs solar+grid when shore power exists
- Panel hiding strategy on site
- Whether Artefact installs LEDs or only delivers shell

### Working calendar (board dates, 2026-08-26)

Live on [Glowberry — R&D](https://github.com/users/adamsimms/projects/2) as **Start Date** and **Due date**. Hard dates are real call deadlines. Everything else is a working target and may slip. This is not the funded-project start after Canada Council (see §10).

| Issue | Start | Due | Kind |
|-------|-------|-----|------|
| [#54](https://github.com/adamsimms/glowberry/issues/54) Eastern Edge apply | 2026-08-26 | 2026-09-14 | Hard |
| [#16](https://github.com/adamsimms/glowberry/issues/16) 3D model package | 2026-08-26 | 2026-09-05 | Working |
| [#17](https://github.com/adamsimms/glowberry/issues/17) Sketches | 2026-08-26 | 2026-09-12 | Working |
| [#64](https://github.com/adamsimms/glowberry/issues/64) Photogrammetry berry tests | 2026-08-26 | 2026-09-04 | Working |
| [#61](https://github.com/adamsimms/glowberry/issues/61) Test prints | 2026-09-03 | 2026-09-19 | Working |
| [#21](https://github.com/adamsimms/glowberry/issues/21) Lighting / power | 2026-09-08 | 2026-09-26 | Working |
| [#57](https://github.com/adamsimms/glowberry/issues/57) The Rooms AIR apply | 2026-09-15 | 2026-11-02 | Hard |
| [#37](https://github.com/adamsimms/glowberry/issues/37) Send Artefact form | 2026-09-15 | 2026-09-22 | Working |
| [#62](https://github.com/adamsimms/glowberry/issues/62) Stage / anchors | 2026-09-15 | 2026-09-30 | Working |
| [#38](https://github.com/adamsimms/glowberry/issues/38) Budget | 2026-09-22 | 2026-10-10 | Working |
| [#26](https://github.com/adamsimms/glowberry/issues/26) Timeline / work plan | 2026-09-22 | 2026-10-10 | Working |
| [#63](https://github.com/adamsimms/glowberry/issues/63) Figma pitch | 2026-09-29 | 2026-10-17 | Working |
| [#27](https://github.com/adamsimms/glowberry/issues/27) Lock M1 | 2026-10-13 | 2026-10-24 | Working |
| [#34](https://github.com/adamsimms/glowberry/issues/34) Site letters | 2026-10-20 | 2026-11-14 | Working (no partner SLA) |
| [#47](https://github.com/adamsimms/glowberry/issues/47) Canada Council apply | 2026-10-20 | 2026-11-21 | Working (rolling intake) |
| [#12](https://github.com/adamsimms/glowberry/issues/12) Site scoring | 2026-11-03 | 2026-11-21 | Parked window |
| [#50](https://github.com/adamsimms/glowberry/issues/50) Futurefarmers AIR | 2026-11-24 | 2026-12-18 | Personal target (rolling) |
| [#51](https://github.com/adamsimms/glowberry/issues/51) CT jam jar | 2026-12-01 | 2027-01-31 | Optional spike |
| [#53](https://github.com/adamsimms/glowberry/issues/53) Structured light | 2027-02-01 | 2027-03-15 | Optional spike |
| [#52](https://github.com/adamsimms/glowberry/issues/52) Photogrammetry on site | 2027-07-15 | 2027-08-31 | Next harvest window |

Milestone 1 target: 2026-10-24. Milestone 2 target: 2026-11-21 (CCA working submit).

---

## 10. First-wave funding (locked 2026-08-26)

| | |
|--|--|
| **Program** | [Canada Council Artistic Creation](https://canadacouncil.ca/funding/grants/explore-and-create) (Explore and Create). Rolling intake. Results usually within about 5 months. |
| **Ask** | Full build of the **~6 ft** 3D-printed outdoor pilgrimage sculpture: translucent shell, heartbeat / breathing glow, power. Not research-only. Not the inflatable track. |
| **Portal** | Profile already validated. |
| **Site** | Still TBD. Longlist in [`SITE.md`](SITE.md): Fogo and Bonavista Peninsula as partner-led regions; Avalon options The Battery, Quidi Vidi, Pouch Cove, Ferryland Head, Cape Spear. Signal Hill dropped. Not near Pinchard's. No permissions claimed. |
| **Quote path** | Studio Artefact one-piece first (form in §7-8) after a quote-ready 3D package. 1 m³ split printers are backup. No invented quotes. |
| **Start date** | Must sit after the Council decision wait. Do not set a project start before results. |
| **Deadlines** | Canada Council: rolling (start date after ~5 month wait). Eastern Edge: 2026-09-14 ([#54](https://github.com/adamsimms/glowberry/issues/54)). The Rooms AIR: 2026-11-02 ([#57](https://github.com/adamsimms/glowberry/issues/57)). |
| **Later** | Gallery tiers A/B and ~7-10 ft stay later. Inflatable is out. Small test prints of the 6 ft mesh are process work now ([#61](https://github.com/adamsimms/glowberry/issues/61)), not a later track. |

GitHub: working sequence [#16](https://github.com/adamsimms/glowberry/issues/16) → [#61](https://github.com/adamsimms/glowberry/issues/61) → [#37](https://github.com/adamsimms/glowberry/issues/37) → [#62](https://github.com/adamsimms/glowberry/issues/62) → [#17](https://github.com/adamsimms/glowberry/issues/17) → [#63](https://github.com/adamsimms/glowberry/issues/63). Site list [#11](https://github.com/adamsimms/glowberry/issues/11), map [#13](https://github.com/adamsimms/glowberry/issues/13), and shortlist [#14](https://github.com/adamsimms/glowberry/issues/14) closed. Sends wait on the pitch, then [#34](https://github.com/adamsimms/glowberry/issues/34). Shop pick [#18](https://github.com/adamsimms/glowberry/issues/18) closed. CCA application is [#47](https://github.com/adamsimms/glowberry/issues/47).

---

*Updated 2026-08-26. First-wave: Canada Council Artistic Creation for the ~6 ft 3D-print full build. Working calendar on the R&D board.*
