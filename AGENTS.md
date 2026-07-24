# Agent notes

Glowberry is developed primarily with Cursor, in the open. Prefer **one milestone (or one issue) per chat** when the work is mechanical.

## Canonical docs

1. [docs/BRIEF.md](docs/BRIEF.md) — concept, tiers, quote draft  
2. [docs/POWER.md](docs/POWER.md) — light / battery / solar / controller  
3. [docs/INFLATABLE.md](docs/INFLATABLE.md) — ephemeral summer track  
4. [docs/RESEARCH_sculpture_precedents.md](docs/RESEARCH_sculpture_precedents.md) — precedents  
5. [docs/BIBLIOGRAPHY.md](docs/BIBLIOGRAPHY.md) — living bibliography (readings / research)  

Also: [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md), [LICENSE.md](LICENSE.md).

## GitHub Projects

- Active: **Glowberry — R&D** — https://github.com/users/adamsimms/projects/2  
- Later (do not create until needed): Fabrication, Editions, Outputs, Web  

Put M1/M2 work on R&D. Do not invent parallel boards without an explicit ask.

## Hard rules

- Do **not** invent site permissions, landowner agreements, fabricator quotes, or funding commitments.
- Do **not** commit moodboard media, location photo dumps, Blender/STL/OBJ, or large binaries unless an issue **explicitly** asks and the artist confirms.
- Locked concept lives in `docs/BRIEF.md`; open spikes belong in issues labeled `decision` or `spike`.
- Dual license: docs/creative → CC BY-NC 4.0; software → MIT. See [LICENSE.md](LICENSE.md).
- Never use the word “master” in new user-facing text, docs, comments, or identifiers (prefer *default branch*, *canonical*, *primary*).
- Controller path is ESP32/Arduino-class — not Raspberry Pi for v1 heartbeat (Pi only if a future Cloudberry-style sensing chapter).

## Model routing (guidance)

| Prefer | When |
|--------|------|
| Judgment-heavy model | Concept, site ethics, grant narrative, tone |
| Fast / mechanical model | Docs moves, templates, labels, git hygiene once decided |

Pattern: `Work issue #N — … Follow docs/BRIEF.md and AGENTS.md.`
