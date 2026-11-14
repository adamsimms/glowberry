# Bakeapple — project brief

Canonical brief for concept, fabrication (Studio Artefact), and systems. Budget open / may pursue funding.

**Project title:** *Bakeapple* (a bakeapple / cloudberry pilgrimage sculpture; earlier working title Glowberry, still the repo and file name).

| Companion docs                                                         |                                                                    |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [`RESEARCH_sculpture_precedents.md`](RESEARCH_sculpture_precedents.md) | Sculpture / material precedents                                    |
| [`BIBLIOGRAPHY.md`](BIBLIOGRAPHY.md)                                   | **Living bibliography** — readings, texts, research                |
| [`MATERIALS.md`](MATERIALS.md)                                         | Print materials, coatings, translucency, mass bands                |
| [`POWER.md`](POWER.md)                                                 | Lighting, battery, solar, controller detail                        |
| [`SITE.md`](SITE.md) | NL site longlist (no place chosen; no permissions claimed) |
| [`INFLATABLE.md`](INFLATABLE.md)                                       | Archived: Choi-lineage inflatable, out since 2026-08-26 |

---

## 1. Concept (locked)

***Bakeapple*** — monumental ripe bakeapple (cloudberry) as an accessible pilgrimage sculpture. One small berry is asked to hold what the island knew, without pretending to preserve what is gone; the size answers how small the berry is.

**Naming and ethics:** keep the Newfoundland word *bakeapple*; acknowledge cloudberry, appik, aqpik and chicouté; do not speak for other communities' traditions. One specific berry, not a generic one. Family are collaborators, not subjects.

|                      |                                                                                                                                                                |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tone**             | Awe + humor + uncanny presence                                                                                                                                 |
| **Body**             | Resettled object — returned / transplanted “soul” (artist in Montreal; work for Newfoundland)                                                                  |
| **Not**              | Weather station, enterable pavilion, data dashboard                                                                                                            |
| **Yes**              | Beacon fruit people travel to see; soft **heartbeat / breathing glow**                                                                                         |
| **Audience**         | Newfoundlanders _and_ visitors                                                                                                                                 |
| **Practice lineage** | Continues _Cloudberry_ (presence / solar failure), _Light House_ (beacon), _Driftwood_ / _Adrift_ (live systems), bakeapple as reason for return to Pinchard’s |

---

## 2. Interaction & siting (locked)

|                         |                                                                                          |
| ----------------------- | ---------------------------------------------------------------------------------------- |
| **Allowed**             | Touch, sit near, walk around, photograph                                                 |
| **Not allowed**         | Entering the interior                                                                    |
| **Site**                | TBD — Avalon, Fogo, or other **reachable** NL location; permissions-dependent            |
| **Landscape character** | Inland of shore / rock or cliff plateau; open coastal view                               |
| **Site mock**           | Local moodboard only for now (not in repo); coastal plateau / shore–cliff character      |
| **Pedestal**            | Not required in art direction (fruit “landed/grown”); fabricator may need hidden anchors |

---

## 3. Material & light (locked)

**Target:** semi-opaque **translucent glowing orange** — light _in the flesh_.

|                   |                                                                                                                                              |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| **Look**          | Saturated amber → vermillion; soft internal luminescence                                                                                     |
| **Build**         | Hollow shell + diffusion + internal LEDs + hatch at stem/bottom                                                                              |
| **Candidates**    | Translucent **FRP / fiberglass–resin**; translucent **PETG** (Artefact); light-passing tints/clearcoats — see [`MATERIALS.md`](MATERIALS.md) |
| **Avoid**         | Fully opaque paint (kills glow); polished stainless as primary skin                                                                          |
| **When it glows** | **Dusk / night** is the show — no daytime glow requirement                                                                                   |
| **Behavior**      | Simple breathing / heartbeat pulse (ESP32-class MCU)                                                                                         |
| **Darkness**      | Outdoor: occasional dark nights **OK** (part of the work)                                                                                    |

---

## 4. Power (locked)

| Scale                          | Role                                               | Power                                                                                                                                          |
| ------------------------------ | -------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **≤ ~60"** (Tiers A & B)       | Gallery / indoor or short outdoor loans            | **AC plug-in** and/or small **battery pack**; typical **5–8 h** evening run; recharge or plug overnight / closed hours; **no solar**           |
| **~10 ft** (Tier C)            | Outdoor landmark                                   | **Solar** (panels **hidden** in/under base); **grid assist OK** if site allows; battery for night; dark spells OK                              |
| **~6 ft**                      | Outdoor-capable pilgrimage; portable lighting test indoors | **Test:** AC + **600-1000 Wh** LiFePO₄, optional visible foldable where allowed, DC into the driver. **Final site:** solar-only vs solar+grid open. |

**Controller:** ESP32 / Arduino / small LED controller — **not** Raspberry Pi (Pi only if a future Cloudberry-style sensing chapter).

Detail + cost bands: [`POWER.md`](POWER.md).

---

## 5. Primary art references

| Reference                                                                                                                     | Steal                                                                   | Don’t copy                                                |
| ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------- |
| **Yayoi Kusama — Yellow Pumpkin** (Naoshima)                                                                                  | Pilgrimage fruit; island landmark; FRP outdoor fruit; recovery hardware | Opaque paint; polka-dot identity                          |
| **Paresh Maity — bronze jackfruit**                                                                                           | Monumental fruit as cultural metaphor                                   | Bronze / no glow                                          |
| **Anish Kapoor — Cloud Gate (Chicago Bean)**                                                                                  | Touchable public body; walk-around uncanny scale                        | Mirror stainless as primary skin                          |
| **James Turrell — Skyspaces**                                                                                                 | Night presence; light as medium; glowing shell logic                    | Enterable architecture as the work                        |
| **Leo Villareal — Buckyball** ([Madison Square Park](https://madisonsquarepark.org/art/exhibitions/leo-villareal-buckyball/)) | Light-as-sculpture; public night draw; programmed LED “life”            | Open lattice / RGB spectacle; complex generative software |
| **Choi Jeong-hwa — inflatable fruit**                                                                                         | Pop humor; photo magnetism; soft temporary monument                     | Don’t treat as the permanent NL beacon                    |

**Stance:** Kusama site + fruit pilgrimage + Turrell/Villareal night light + Kapoor touchability → **translucent FRP/PETG flesh** with a **simple heartbeat**, not a Buckyball-style LED cage.

**Inflatable:** out since 2026-08-26; notes archived in [`INFLATABLE.md`](INFLATABLE.md).

---

## 6. Fabrication files (Studio Artefact)

Production mesh package is **not published in this repo yet** (will be added deliberately when quote-ready). Local working files live outside git for now.

**Body origin (open, OD below):** the application texts say the body descends from the **provenance scan** of a Pinchard's Island bakeapple picked by the artist's grandmother ([`SCANNING.md`](SCANNING.md)): raw scan as ancestor and archive twin, print path a cleaned, manifold descendant. Since the v17 test prints the body is modelled from reference photos, which `SCANNING.md` calls a departure from that claim. Which body the 6 ft piece and the editions use is not decided; public text must not claim more than is true.

When publishing, expect roughly:

| File                                 | Use                                               |
| ------------------------------------ | ------------------------------------------------- |
| `glowberry_master_500mm.stl`         | Production mesh (~484k tris), sent by file transfer |
| `glowberry_master_500mm_preview.stl` | Lighter preview                                   |
| `glowberry_master_500mm.obj`         | Alternate format                                  |
| `glowberry.blend`                    | Blender source (optional)                         |
| Berry / site refs                    | Curated references (added intentionally later)    |

**Units:** meters; master height **500 mm**. Scale uniformly per tier.

### Geometry

- Drupelets only (no calyx, stem, leaves, hairs)
- Manifold / watertight
- ~447 × 460 × **500 mm**
- **−Z = stem/attachment** (bottom when upright)
- STL uncolored — translucency + LEDs + power are separate scope

### Scale tiers

| Tier                       | Height                          | Scale from 500 mm | Role                                   | Fabrication note                                                                                        |
| -------------------------- | ------------------------------- | ----------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Primary (Artefact ask)** | **~6 ft (≈1.8 m)**              | **≈3.66×**        | Outdoor-capable pilgrimage piece       | **20 m³ one-piece only**; translucent PETG ± weather coat. Split/join is not a live path for this size. |
| A (later)                  | 20–30"                          | 1.02×–1.52×       | Gallery / study                        | Smaller prints possible                                                                                 |
| B (later)                  | 50–60"                          | 2.54×–3.05×       | Gallery                                | Later; not a split of the 6 ft piece                                                                    |
| C (alt.)                   | ~7–10 ft                        | 4.3×–6.1×         | Larger landmark                        | Same family as 6 ft; not the current quote focus                                                        |
| Editions (now)             | 10 to 16 in (about 25 to 40 cm) | 0.51x to 0.81x    | Small ownable objects, lit from inside | See **Small editions** below; method and material under test                                            |

**Current submission to Artefact:** quote the **~6 ft** piece only. Shop may hollow, rib, thicken walls; advise on translucent outdoor builds.

### Small editions (decided 2026-10-27; method 2026-11-09)

The ~6 ft piece stays the primary vision. It depends on grants and funding and will take a long time. In the meantime the artist is making smaller, ownable objects (editions) of the berry, about 10 to 16 in tall (25 to 40 cm) and lit from inside, and is testing print methods and materials now to see what works best for them. Edition size, count and price are not set. Every small berry is an edition of the work, including residency batches and studies; solar printing (a printer on its own panel and battery, pausing when the battery runs dry) with a logged energy record is part of how they are made ([`POWER.md`](POWER.md#solar-print-logger-editions)).

The 100 mm v17 test prints out for quotes at Proto3000, MatterThings, Objex Unlimited and 3DMan ([`SCANNING.md`](SCANNING.md), [`FABLABS.md`](FABLABS.md)) are a cheap first comparison toward these editions. They are not a test of the 6 ft FDM shell, so PolyJet, SLA and SLS samples are expected to look different from the final sculpture.

Size limits at edition scale:

| Process                              | Build height           | At 10 to 16 in                   |
| ------------------------------------ | ---------------------- | -------------------------------- |
| Stratasys J750 PolyJet (full colour) | About 200 mm           | No one-piece full-colour berry   |
| Mimaki 3DUJ-553 (Objex Unlimited)    | 305 mm                 | 10 to 12 in fits; 16 in does not |
| Large-format SLA and SLS             | Depends on the machine | Usually reaches 14 to 16 in      |

The artist will compare methods on:

- Look when lit from inside: translucency, evenness of the glow, darker seams between drupelets
- Colour in the material rather than paint (amber #F79523 to red-orange #ED541F)
- Surface detail and finish at that scale
- Durability and handling for owned objects
- Rough cost per piece for a small edition

Next step: ask each service for a recommendation and a rough price for one piece at about 12 in.

---

## 7. Contact — Studio Artefact

**Official path:** their [project contact form](https://www.studioartefact.com/en/contact/) (not a free-form cold email alone).

Paste-ready answers + PDF brief: [`docs/artefact/`](artefact/).

Form fields they ask for:

| Field              | Suggested for Glowberry                                                                                                            |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| Project type       | **3D printing**                                                                                                                    |
| Delivery           | **In more than six months** (exploratory / grant-dependent)                                                                        |
| Budget band        | **$50,000 or less** for this feasibility ask (or $50–100k if you prefer)                                                           |
| Description        | Paste from [`artefact/FORM_ANSWERS.md`](artefact/FORM_ANSWERS.md) — **~6 ft only**                                                 |
| Documents          | PDF from [`artefact/ARTEFACT_SUBMISSION_BRIEF.md`](artefact/ARTEFACT_SUBMISSION_BRIEF.md) + preview image; full STL via WeTransfer |
| How you found them | e.g. online search / recommendation                                                                                                |
| Email / phone      | Required                                                                                                                           |

**Also:** 514-933-7666 · info@studioartefact.com · 7900 av. Blaise-Pascal, Montreal

### Best approach

1. **Submit the form** with the short **6 ft** brief + clear feasibility ask.
2. After they reply, **co-design** materials, translucent coat, hatch, wall thickness.
3. Keep the first ask to **feasibility / ballpark range**, not a hard PO.

### Form body (short — ~6 ft)

**Specifically:** Quote / feasibility — Glowberry, translucent glowing bakeapple, **~6 ft**

Hello, Adam Simms, Montreal. Developing **Glowberry** (bakeapple / cloudberry pilgrimage sculpture) with soft internal heartbeat glow. Touchable; walk-around; no entry. NL outdoor site TBD. Funding open. Please treat as **feasibility + rough range** for **one size: ~6 ft (≈1.8 m)** tall, scaled from a 500 mm manifold mesh (≈3.66×). Prefer translucent PETG ± translucent outdoor coat (or FRP if needed); hatch at stem; LEDs may be separate scope. **One-piece print required** (20 m³ class). Not a split/join. Cost range, wall/mass, coastal weather finish, timeline. Brief PDF + refs attached; full STL on WeTransfer on request. https://github.com/adamsimms/glowberry. Thanks, Adam · hello@adamsimms.xyz · [Phone]

---

## 8. Send checklist

- [ ] Fill [Artefact contact form](https://www.studioartefact.com/en/contact/) (3D printing + timeline + budget band)
- [ ] Upload **6 ft** PDF brief (+ preview image); WeTransfer full STL if asked
- [ ] Name / phone / email on form
- [ ] Stress **translucent / glow-capable** + **~6 ft one-piece only** (no split)
- [ ] Ask for **feasibility + range**, not a fixed PO yet
- [ ] Interaction: touch / sit near / walk around — no entry

---

## 9. Still open

Dates live on the [R&D board](https://github.com/users/adamsimms/projects/2), not here.

- Body source for the 6 ft piece and the editions: the provenance scan or the v17 reference-photo body (see section 6)
- Exact NL site + permissions
- Outdoor power at the final site: solar-only vs solar+grid when shore power exists
- Panel hiding strategy on site
- Alternate quotes beside Artefact ([#37](https://github.com/adamsimms/glowberry/issues/37)): [AllPrototype](https://allprototype.com/3d-scanning-montreal/), [USIMM](https://www.usimm.ca/en/)

## 10. Decisions log

- 2026-11-09: Title is *Bakeapple* (was Glowberry). The repo and file names stay `glowberry` until a rename is decided.
- 2026-11-09: Every small berry (studies, residency batches, the 10 to 16 in lit pieces) is an edition; solar printing with a logged energy record is part of how they are made. Section 6, `POWER.md`.
- 2026-11-09: The artist installs the LEDs after the shell arrives (was open: whether Artefact installs them).
- 2026-11-09: Concept line, naming ethics, family as collaborators. Section 1.
- 2026-11-09: No site outreach is sent before the pitch package exists (pitch, budget, sketches, scale). Contacts may be recorded.
- 2026-11-09: Body source reopened (scan vs v17); section 6 no longer says locked.
- 2026-10-27: Small lit editions (10 to 16 in) beside the 6 ft vision.
- 2026-10-17: 6 ft shell is one piece only.

---

