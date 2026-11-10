# Bakeapple — power & lighting

Companion to [`BRIEF.md`](BRIEF.md). Locked decisions from project development (2026-07).

Print / coating / translucency / mass bands: [`MATERIALS.md`](MATERIALS.md).

---

## Locked decisions

| Topic | Decision |
|-------|----------|
| Glow behavior | Soft **heartbeat / breathing** pulse only — no weather dashboard |
| When it glows | **Dusk / night** (no daytime glow requirement) |
| Controller | **ESP32 / Arduino / small LED controller** — not Raspberry Pi |
| Darkness outdoors | **OK** — part of the work (Cloudberry kinship) |
| Panels | **Hidden** in/under base (not on the fruit) when solar is used |
| **≤ ~60" (Tiers A & B)** | **Gallery:** ~**5–8 h** evening run; **AC plug-in** and/or small **battery pack**; recharge/plug overnight; **no solar** |
| **~10 ft (Tier C)** | **Outdoor:** **solar** (hidden) + battery; **grid OK if site allows** |
| **~6 ft** | Outdoor-capable. **Lighting test: AC + battery; optional bounded solar** (visible panel charging the pack, where allowed). Final-site power open (solar-only vs solar+grid). |

---

## Tier A & B (≤60") — gallery appliance

### Duty cycle
- Typical exhibition: **5–8 hours** per evening  
- Daytime: off or unplugged  
- Overnight: **charge** or leave **plugged in** during closed hours  

### Why this is easy
- Soft pulse might average on the order of **~5–20 W** while glowing (scale-dependent)  
- 8 h × 15 W ≈ **120 Wh** — a modest LiFePO₄ pack or a hidden IEC inlet covers it  
- MCU draw is negligible  

### Recommended stack
```text
[Gallery AC] ──optional──► [12/24V supply] ──► [LED driver] ← [ESP32 PWM]
                                ▲
                         [Battery pack]
                         (backup / cable-free nights)
```

| Approach | When to use |
|----------|-------------|
| **Plug-in primary** | Permanent gallery install with floor box / wall outlet |
| **Battery primary** | Clean floor, temporary hang, no visible cable |
| **Both** | Plug when possible; battery for openings / power cuts |

**Access:** hatch at stem/bottom for pack swap or charge port.

**Cost band (electronics only, CAD, rough):** ~$200–800 for a solid gallery LED + MCU + small pack/supply (shell separate).

---

## ~6 ft portable lighting test (not the landscape power plant)

The 6 ft piece is outdoor-capable. An indoor or studio **lighting test** (for example during a residency) still uses the gallery stack:

```text
[Studio AC] ──► [12/24V supply] ──► [LED driver] ← [ESP32 PWM]
                      ▲
               [LiFePO₄ pack]
                      ▲
         optional [visible PV]  (only where the host allows)
```

- **Grid** in the studio (plug-in primary). Ask which circuit; do not assume an outdoor outlet.
- **Battery** so the fruit can sit without a cable, so you can practice dim-then-**allow dark**, and so a short evening outside does not depend on an outdoor receptacle.
- **Optional bounded solar:** one foldable suitcase panel charging a LiFePO₄ power station that also AC-charges in the studio. Visible, portable, in overnight. Prefer **DC out** into the LED driver. Not hidden in the base, not a bermed enclosure, not the landscape plant. If the panel does not keep up, darkness is the Cloudberry result. Wind: foldable panels are sails; bring them in. Landscape PV stays [#21](https://github.com/adamsimms/glowberry/issues/21) / the eventual site.
- Peak LED for ~6 ft: treat as **between** the 50-60" and ~10 ft bands (order of **~30-80 W** until measured). An 8 h evening is still pack-scale, not array-scale.
- Outside (if ever): splash-aware cabling, in overnight. Not IP65 landscape commission.

### Portable kit (spec band, not a SKU)

Energy, until wattage is measured:

| Planning case | Draw | 8 h evening |
|---------------|------|-------------|
| Pulse average | ~15-40 W | ~120-320 Wh |
| Peak held all night | ~80 W | ~640 Wh |

Studio wall charge covers the next day. The pack only has to own **one evening** plus a little cold/loss headroom. A 2000 Wh camping station hides the solar test: the fruit never needs the panel.

| Piece | Band | Why |
|-------|------|-----|
| Station | **600-1000 Wh** LiFePO₄, brick **under ~12 kg** | One evening at 6 ft; one person carries it in at night |
| Panel | **One 200-220 W** foldable, matched to the station's solar ceiling | ~2-4 equivalent sun hours downtown is enough to replace a modest evening on a decent day. 100 W is too tight. A second 200 W panel is wasted if the station caps at ~220-300 W, and is a second sail in harbour wind |
| LED feed | **12 V DC out** (car/XT60/Anderson into the driver). Inverter **off** unless you need a tool | Station DC around 12 V / 10 A (~126 W) covers 80 W peak. Inverter idle (often 8-20 W) can rival a dim fruit |
| Charge | Wall AC in the studio. Solar only where a visible test is allowed | Grid is primary |

Products iterate: buy to the band when needed, not ahead.

Orientation only (Canada, prices move): EcoFlow RIVER 2 Pro (768 Wh, 7.8 kg, 220 W solar max, 12.6 V / 10 A DC) plus **one** 220 W portable panel, kit about C$900-1100. Same band: Anker SOLIX C800 (768 Wh, ~10.5 kg, 300 W solar max) plus one 200 W foldable. A 2400 W / 2160 Wh station with two 200 W cases is the wrong class: heavy, AC-idle hungry, and too much storage for the test to matter.

This kit is **not** the landscape plant (hidden PV, buried enclosure, MPPT).

---

## Tier C (~10 ft) — outdoor energy system

### Architecture
```text
[Hidden PV] → [MPPT charge controller] → [Battery + BMS]
                                              ↓
                               [LED driver] ← [ESP32]
                                              ↓
                                    [Diffused LEDs in berry]
```

Optional: **grid charger / hybrid** when pier, building, or arts centre power exists.

### Physical layout
- **Berry:** translucent shell, LEDs, driver, MCU (or tray that lifts out)  
- **Enclosure (under/beside, bermed or rock-clad):** batteries, MPPT, disconnects  
- **Panels:** low, south-ish, screened — not on orange flesh  
- **Conduit:** buried berry ↔ enclosure  
- **Hatch:** berry bottom + enclosure lid  

### Behavior
- Day: off  
- Night: breathe  
- Low battery: dimmer/slower, then **allow dark**  

### Ballpark systems cost (CAD, not sculpture shell)

| Item | Rough range |
|------|-------------|
| LEDs + drivers + diffusion | $1,000–3,000 |
| ESP32 + weatherproofing | $100–400 |
| PV array (hidden) | $1,200–3,500+ |
| MPPT | $300–800 |
| LiFePO₄ + BMS | $2,000–6,000+ |
| Conduit, enclosure, protection | $800–2,000 |
| Install / commission | $2,000–6,000 |
| **Systems subtotal** | **~$7k–22k** (NL winter → high end) |

Sculpture shell (Artefact / FRP) is **separate** and typically larger.

---

## LED fill (order-of-magnitude)

| Scale | Peak LED (soft glow) | Notes |
|-------|----------------------|--------|
| 20–30" | 5–15 W | Gallery battery/plug trivial |
| 50–60" | 20–50 W | Still fine for 5–8 h gallery |
| ~6 ft | ~30–80 W (until measured) | Lighting test: plug + pack. Not a PV sizing driver. |
| ~10 ft | 50–120 W | Drives solar/grid sizing |

Use warm white + amber/orange (or tuned RGBW); diffuse so no hotspots; IP65+ outdoors.

---

## Why not Raspberry Pi?

| | Pi | ESP32 / Arduino |
|--|-----|-----------------|
| Idle power | ~2–5 W | Milliwatts–low watts |
| Role | Cameras, cellular, servers | PWM heartbeat |
| Fit | Future Cloudberry 2.0 sensing | **Glowberry v1** |

---

## Solar-print logger (editions)

A separate, small system for printing the editions. It does not power or control the large sculpture's heartbeat.

Editions are printed on a small 3D printer running on its own portable panel and battery, pausing when the battery runs dry, so available stored energy conditions each print. A low-power ESP32 or Arduino-class logger will record the energy system around each attempt.

```text
[portable panel] → [charge controller / power station] → [small 3D printer]
                           ↓
                    [ESP32 energy logger]
```

### Record for each attempt

- energy captured from the panel during the relevant period, in Wh where the system permits measurement
- battery state at the start and end of the attempt
- printer draw and print duration where practical to measure
- a brief manual note on panel angle, shade, wind, and cloud
- the working-file version, print state, and any finishing operation

The record is provenance, not a weather dashboard. Solar capture reflects panel placement, shade, charge state, conversion loss, and sun. The log makes the record accountable; do not claim that weather automatically generates form.

The logger, sensors, and any small enclosure are artist-supplied. The final sensing architecture and printer-power measurement remain research questions. Do not assume that the lighting kit specified above can power the printer.

---

## Open systems questions

- Tier C / 6 ft **landscape** site: solar-only vs solar+grid when shore power exists
- Exact enclosure/panel hiding with landscape architect / engineer
- Gallery cable management aesthetic (visible cloth cord vs floor pocket)
- 6 ft measured wattage (locks the 15-40 W vs 80 W case). Pack/panel **band** is set (600-1000 Wh + one 200-220 W foldable); the SKU waits until needed.

---

