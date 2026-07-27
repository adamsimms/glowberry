# Glowberry — power & lighting

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
- **Vault (under/beside, bermed or rock-clad):** batteries, MPPT, disconnects  
- **Panels:** low, south-ish, screened — not on orange flesh  
- **Conduit:** buried berry ↔ vault  
- **Hatch:** berry bottom + vault lid  

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
| Conduit, vault, protection | $800–2,000 |
| Install / commission | $2,000–6,000 |
| **Systems subtotal** | **~$7k–22k** (NL winter → high end) |

Sculpture shell (Artefact / FRP) is **separate** and typically larger.

---

## LED fill (order-of-magnitude)

| Scale | Peak LED (soft glow) | Notes |
|-------|----------------------|--------|
| 20–30" | 5–15 W | Gallery battery/plug trivial |
| 50–60" | 20–50 W | Still fine for 5–8 h gallery |
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

## Open systems questions

- Tier C site: solar-only vs solar+grid when shore power exists  
- Exact vault/panel hiding with landscape architect / engineer  
- Who supplies LEDs: Artefact vs separate systems fabricator  
- Gallery cable management aesthetic (visible cloth cord vs floor pocket)  

---

*Updated 2026-07-22*
