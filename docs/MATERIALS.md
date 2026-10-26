# Glowberry — materials (print, coatings, translucency)

Notes for keeping **3D printing** and **translucent flesh glow** under Newfoundland outdoor stress (UV, freeze–thaw, salt). Companion to [`BRIEF.md`](BRIEF.md), [`POWER.md`](POWER.md), [`RESEARCH_sculpture_precedents.md`](RESEARCH_sculpture_precedents.md).

---

## Reality check

Raw FDM plastic at landscape scale is **not** a decade-proof coastal skin by itself. Print is excellent for **gallery pieces, masters/molds, and short outdoor tests**. Permanent NL survival usually means **coatings** and/or **print as core/tooling** under a weather face.

Lighting vs ribs: see issue discussion on luminous volume vs structure ([#21](https://github.com/adamsimms/glowberry/issues/21)).

---

## Best print material (for translucency)

| Material | Translucency | Outdoor without coat | Role |
|----------|--------------|----------------------|------|
| **PETG** (clear / natural) | Good | Weak–medium | **Default** — toughness + printability + light pass |
| **PC** (clear) | Good | Weak (UV) | More cold/impact toughness; harder large-format print |
| **ASA** (natural/clear if available) | OK–good | Better UV than PETG | Often less “juicy” optically |
| PLA / filled / opaque | Poor | No | Skip for Glowberry flesh |

**Tint strategy:** print **clear or lightly amber**; put saturated orange in a **thin translucent coat** so UV hits the finish first.

**Test prints are orange or amber from the start**, never neutral grey (decided 2026-10-17). Desk tests use orange or amber filament and resin; full-colour service tests use the files in `models/print/colour/` (see [`SCANNING.md`](SCANNING.md)). Where to print desk tests in Montreal: [`FABLABS.md`](FABLABS.md).

Artefact-class large-format **translucent PETG** remains the primary shop conversation for printable shells ([`BRIEF.md`](BRIEF.md) tiers).

---

## Coatings that still allow translucency

Prefer **thin + UV-stable + aliphatic**. Thick opaque gelcoat protects weather and kills glow.

### A — Print is the visible skin

| Coating | Translucency | Weather / UV | Notes |
|---------|--------------|--------------|-------|
| **Aliphatic polyurethane clear** (marine / exterior) | Yes if thin & clear | Best common clear outdoor topcoat | Top pick over sealed PETG |
| **Clear automotive 2K urethane** | Yes | Good | Needs adhesion promoter on PETG; coupon-test |
| **UV acrylic / plastic-compatible clear spray** | Yes | Medium–good | Prototypes, gallery, short outdoor |

Avoid as sole outdoor clear: craft epoxy (yellows), aromatic PU, indoor varnish.

### B — Thin translucent resin skin over print (sweet spot)

| System | Translucency | Notes |
|--------|--------------|-------|
| Thin clear / **tinted translucent** polyester or epoxy laminating resin | Yes if not opaque-pigmented | Print = core; resin = weather face |
| **Translucent tinted gelcoat** (orange + UV package) | Yes if formulated translucent | Stronger outdoor; closer to FRP |
| Translucent tinted base + **aliphatic UV clear** | Yes | Orange in base, UV clear on top |

### C — Print as tooling only (most resilient)

Print master → mold → cast/spray **translucent FRP** (or shop outdoor system). Print never lives in salt/winter.

---

## Ranked paths (print + glow + NL)

1. **Gallery / short outdoor:** PETG translucent + thin aliphatic clear.  
2. **Serious outdoor, still print-based:** PETG (or PC) shell → seal seams → thin translucent orange resin/gelcoat → aliphatic UV clear + internal LEDs/diffusion.  
3. **Permanent coastal landmark:** print for mold/master → translucent FRP / engineered composite.

---

## Process checklist

- Seal layer lines and joints (water + freeze love them)  
- Degrease; **plastic adhesion promoter** for PETG  
- Coupon-test: same filament + coat + UV + wet freeze before committing  
- Prefer **satin/matte** clear outdoors (hides print texture; less glare)  
- Separate **structure** from **luminous volume** (ribs behind diffuser or rib-edge lighting)

---

## Weight estimate — ~7 ft PETG Glowberry

**Assumption:** overall height ≈ **7 ft (2.13 m)** hollow berry (not a solid 7×7×7 ft cube). Density PETG ≈ **1.27 g/cm³**.

Rough shell as sphere of diameter ≈ 7 ft (surface area ≈ 14.5 m²), then **× ~1.4–1.6** for drupelet surface + light internal ribs:

| Wall (avg) | Approx. plastic mass | Order of magnitude |
|------------|----------------------|--------------------|
| **5 mm** | ~90–130 kg | ~200–290 lb |
| **8 mm** | ~150–210 kg | ~330–460 lb |
| **10 mm** | ~180–260 kg | ~400–570 lb |
| **15 mm** | ~280–400 kg | ~620–880 lb |
| **20 mm** | ~370–530 kg | ~820–1170 lb |

**Extra mass (not in table):** base/anchors, battery, LEDs, diffuser, solar hardware — often **+20–80 kg** depending on outdoor vs gallery.

**If “7 feet cubed” meant a solid 7×7×7 ft block of PETG:** ~**12 tonnes** — not applicable to a hollow sculpture.

**Shop reality:** ask Artefact (or printer) for mass from the actual mesh at target wall thickness + infill/ribs; treat the table as planning bands only.

---

## Pure materials cost — ~7 ft PETG (planning bands)

**This is resin/filament + coating chemistry only** — not machine time, labor, shop overhead, failed prints, shipping, or electronics. Those usually dwarf raw plastic on a custom art piece.

### PETG feedstock price (order-of-magnitude, 2026)

| Form | Typical price | Notes |
|------|---------------|--------|
| **Pellets** (large-format / FGF) | ~**CAD $5–20 / kg** landed | Common for 100+ kg jobs; translucent grades toward upper end |
| **Filament** (spools) | ~**CAD $20–40 / kg** | Unlikely for a full 7 ft shell; shop may still bill filament-equivalent |

Use **~CAD $12–25 / kg** as a planning midpoint for translucent PETG on a serious large-format job.

### Plastic-only cost × wall thickness

| Wall | Mass band | @ $12/kg | @ $20/kg | @ $30/kg (filament-ish) |
|------|-----------|----------|----------|-------------------------|
| 5 mm | 90–130 kg | **~$1.1k–1.6k** | **~$1.8k–2.6k** | **~$2.7k–3.9k** |
| 8–10 mm | 150–260 kg | **~$1.8k–3.1k** | **~$3.0k–5.2k** | **~$4.5k–7.8k** |
| 15 mm | 280–400 kg | **~$3.4k–4.8k** | **~$5.6k–8.0k** | **~$8.4k–12k** |
| 20 mm | 370–530 kg | **~$4.4k–6.4k** | **~$7.4k–10.6k** | **~$11k–16k** |

**Likely planning band for a structural outdoor-ish shell (8–15 mm):** roughly **CAD $2k–8k** in PETG alone (pellet economics).

### Coatings (materials only, ~7 ft surface)

| System | Rough materials | Notes |
|--------|-----------------|--------|
| Aliphatic clear topcoat | **~$150–600** | A few litres sprayed/rolled |
| Thin translucent tinted resin / gelcoat + clear | **~$400–2,000** | Chemistry + waste; not labor |
| Adhesion promoters, sealers, sandpaper, masking | **~$50–300** | Easy to forget |

### Ballpark “pure materials” total (print + translucent weather face)

| Build intent | Plastic + coat (CAD) |
|--------------|----------------------|
| Gallery, thinner wall, clear only | **~$1.5k–4k** |
| Outdoor-leaning, 8–15 mm + tinted translucent coat | **~$3k–10k** |
| Heavy wall + generous coating waste | **~$8k–15k+** |

Again: a shop **quote** for a finished 7 ft Glowberry will usually be **much higher** (machine hours, programming, finishing labor, risk). Raw materials are often a **minority** of the invoice.

---

## Transport (6 ft one-piece)

The 6 ft pilgrimage shell is a **single print**. Split/join is not a live path.

Scaled mesh envelope (500 mm × ≈3.66): about **64" × 66" × 72"** (≈1636 × 1684 × 1830 mm). Confirm bbox on the production file ([#16](https://github.com/adamsimms/glowberry/issues/16)).

| Opening | Width | Fit |
|---------|-------|-----|
| 15 ft U-Haul cargo door | 7'3" × 6'5" | Bare shell should fit. Crate may not. Uncrate outside if needed. |
| Eastern Edge studio double doors | 62" | **No.** Do not shrink the sculpture to fake this fit. |
| Eastern Edge garage | 3 m, 12" step from parking lot | **Yes** for width. Ramp or lift for the step. Parked until a residency yes ([#65](https://github.com/adamsimms/glowberry/issues/65), closed). |
| Eastern Edge assigned bay | Studio 1 / Studio 2 split of the open harbour studio (shared, up to three artists plus a writer) | **Yes** for a walk-around. Object is ~1.64 × 1.68 × 1.83 m. Ask for the **garage-side bay (Studio 2)** and about **4 m clear** plus a table. Do not ask for the other studio or exclusive use of the open floor. Steel post sits on the dashed split. Ceiling 12'. |

Eastern Edge application **leads inside**. Why this place: first nights of a returned fruit in a harbour studio that can take the body through the garage, not a landscape sit. Floor ask is the garage-side bay (Studio 2) and walk-around clearance, not extra exclusive space. Outdoor dusk on the parking lot is a staff-shaped option (not a dock, not a promised install). Insurance and vandalism stay parked until a yes ([#66](https://github.com/adamsimms/glowberry/issues/66), closed). A month on the Pier 10 boardwalk across the street is a separate Port Authority stretch, also parked ([#67](https://github.com/adamsimms/glowberry/issues/67), closed). Trucking the shell to and from St. John's is **artist-driven**: printed one-piece at Artefact, driven in a U-Haul by the artist, paid from the sculpture budget, not Eastern Edge's return-shipping stipend. Bare shell should fit a 15 ft cargo door; uncrate outside if the crate does not.

---

*Updated 2026-10-13. Eastern Edge garage, lot, and Pier 10 questions parked until a residency yes.*
