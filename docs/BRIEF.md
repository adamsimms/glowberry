# Glowberry — project brief

Canonical brief for concept, fabrication (Studio Artefact), and systems. Budget open / may pursue funding.

**Project title:** Glowberry (bakeapple / cloudberry pilgrimage sculpture).

| Companion docs | |
|----------------|--|
| [`RESEARCH_sculpture_precedents.md`](RESEARCH_sculpture_precedents.md) | Sculpture / material precedents |
| [`BIBLIOGRAPHY.md`](BIBLIOGRAPHY.md) | **Living bibliography** — readings, texts, research |
| [`MATERIALS.md`](MATERIALS.md) | Print materials, coatings, translucency, mass bands |
| [`POWER.md`](POWER.md) | Lighting, battery, solar, controller detail |
| [`INFLATABLE.md`](INFLATABLE.md) | **Separate track:** ephemeral summer inflatable (Choi-lineage POC) |

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
| **Site** | TBD — Avalon, Fogo, or other **reachable** NL location; permissions-dependent |
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

**Parallel track:** Choi-style **inflatable** as ephemeral summer POC — see [`INFLATABLE.md`](INFLATABLE.md).

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
| **Primary (Artefact ask)** | **~6 ft (≈1.8 m)** | **≈3.66×** | Outdoor-capable pilgrimage piece | Prefer **20 m³** one piece; translucent PETG ± weather coat |
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

Hello — Adam Simms, Montreal. Developing **Glowberry** (bakeapple / cloudberry pilgrimage sculpture) with soft internal heartbeat glow. Touchable; walk-around; no entry. NL outdoor site TBD. Funding open — please treat as **feasibility + rough range** for **one size: ~6 ft (≈1.8 m)** tall, scaled from a 500 mm manifold master (≈3.66×). Prefer translucent PETG ± translucent outdoor coat (or FRP if needed); hatch at stem; LEDs may be separate scope. Advise one-piece vs split, cost range, wall/mass, coastal weather finish, timeline. Brief PDF + refs attached; full STL on WeTransfer on request. https://github.com/adamsimms/glowberry — thanks, Adam · hello@adamsimms.xyz · [Phone]

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

- Exact NL site + permissions  
- Outdoor power: solar-only vs solar+grid when shore power exists  
- Panel hiding strategy on site  
- Whether Artefact installs LEDs or only delivers shell  

---

*Updated 2026-07-27 — Artefact ask simplified to ~6 ft primary tier.*
