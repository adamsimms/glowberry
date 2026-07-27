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

| Tier | Height | Scale from 500 mm | Fabrication note | Power |
|------|--------|-------------------|------------------|--------|
| **A** | 20–30" | 1.02×–1.52× | Prefer **1 m³**, one piece; translucent + LED hatch | Gallery: plug / battery, 5–8 h |
| **B** | 50–60" | 2.54×–3.05× | Quote split on 1 m³ **and** one piece on **20 m³** | Gallery: plug / battery, 5–8 h |
| **C** | ~10 ft | 6.10× | Prefer **20 m³** one piece; outdoor translucent + anchors | Solar (hidden); grid if available |

Shop may hollow, rib, thicken walls; advise on translucent outdoor builds.

---

## 7. Email draft — Studio Artefact

**To:** info@studioartefact.com  
**Subject:** Quote — translucent glowing bakeapple sculpture (Glowberry), three sizes

Hello,

I’m developing **Glowberry**: a bakeapple (cloudberry) sculpture — gallery pieces up to ~60" and a possible ~10 ft outdoor landmark in Newfoundland (site TBD; coastal plateau / rock–cliff character). Budget open / may pursue funding.

**Art direction:** semi-opaque **translucent orange** that can **glow from within** (soft heartbeat pulse). Touchable; walk-around; no entry. References in spirit: Kusama’s Naoshima pumpkin (pilgrimage fruit), Kapoor’s Cloud Gate (public touchable body), Turrell / Villareal (night light) — but materials should **pass light** as flesh, not an open LED lattice, opaque paint, or mirror steel.

Attached / linked: manifold STL at **500 mm** master height, berry photo refs, site character mockup.

Please quote feasibility / ranges for:

### Tier A — 20–30"
- Prefer **1 m³**, one piece  
- Translucent / light-passing build + internal LED access hatch  

### Tier B — 50–60"
- One berry; price **both** split on 1 m³ + join **and** one piece on **20 m³**  
- Same translucent glow intent; gallery power will be plug-in / battery (not your scope unless you offer LED install)  

### Tier C — ~10 ft outdoor
- Prefer one piece on **20 m³**  
- Outdoor UV / weather, anchoring for shore/cliff plateau, hatch for electronics  
- Systems (solar / grid) may be separate — advise if you integrate LEDs / partner on power  

Also: materials you’d recommend for **translucent glowing orange** outdoors (PETG vs FRP handoff, wall thickness, diffusion).

Happy to talk after you’ve glanced at the files.

Best regards,  
[Your name]  
[Phone]

**Contacts:** 514-933-7666 · info@studioartefact.com · 7900 av. Blaise-Pascal, Montreal

---

## 8. Send checklist

- [ ] Upload full STL (WeTransfer / Drive) when mesh package is ready  
- [ ] Attach preview or link + curated berry refs + site character  
- [ ] Name / phone in email  
- [ ] Stress **translucent / glow-capable** materials  
- [ ] Tier A/B = gallery plug/battery; Tier C = outdoor solar/grid (systems may be separate)  
- [ ] Interaction: touch / sit near / walk around — no entry  

---

## 9. Still open

- Exact NL site + permissions  
- Tier C: solar-only vs solar+grid when shore power exists  
- Exact panel hiding strategy on site  
- Whether Artefact installs LEDs or only delivers shell  

---

*Updated 2026-07-22 — consolidates concept, Artefact quote package, and power discoveries.*
