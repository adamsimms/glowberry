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

*Updated 2026-07-27 — print/coating options + ~7 ft PETG mass bands.*
