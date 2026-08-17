# Agent notes

Glowberry is developed primarily with Cursor, in the open. Prefer **one milestone (or one issue) per chat** when the work is mechanical.

## Canonical docs

1. [docs/BRIEF.md](docs/BRIEF.md) — concept, tiers, quote draft  
2. [docs/POWER.md](docs/POWER.md) — light / battery / solar / controller  
3. [docs/INFLATABLE.md](docs/INFLATABLE.md) — ephemeral summer track  
4. [docs/RESEARCH_sculpture_precedents.md](docs/RESEARCH_sculpture_precedents.md) — precedents  
5. [docs/BIBLIOGRAPHY.md](docs/BIBLIOGRAPHY.md) — living bibliography (readings / research)  
6. [docs/MATERIALS.md](docs/MATERIALS.md) — print, coatings, translucency, ~7 ft mass bands  

Also: [README.md](README.md), [CONTRIBUTING.md](CONTRIBUTING.md), [LICENSE.md](LICENSE.md).

Local-only playground: [`sketchpad/`](sketchpad/) (gitignored except its README). Use for drafts and reference material; canonical truth stays in `docs/`.

## Private vault

Working notes live in a local Obsidian vault shared with Rover, Dreamberry, and Camera Philosophies (not this repo). A gitignored Cursor rule names the path on this machine. Start at the Studio Vault Index, then the Glowberry project index (`Glowberry/MOCs/`), then one topical MOC. Glowberry notes live under `Glowberry/`. Filename prefix `Glowberry -`. Do not copy restricted material into this repo. Public `docs/` are the adapted canon. Dual-write decisions and status to `docs/` and the vault in the same turn. Sketchpad is scratch only.

## Bibliography / Zotero

Zotero holds PDFs and the working library. The public living bibliography is [docs/BIBLIOGRAPHY.md](docs/BIBLIOGRAPHY.md). The vault does not sync with Zotero. Do not query `~/Zotero/zotero.sqlite`. Do not invent citations. Sketchpad `zotero_*.py` scripts are one-shot imports, not agent tools.

## GitHub Projects

- Active: **Glowberry — R&D** — https://github.com/users/adamsimms/projects/2  
- Later (do not create until needed): Fabrication, Editions, Outputs, Web  

Put M1/M2 work on R&D. Do not invent parallel boards without an explicit ask.

Priority on the board (and matching `priority:*` issue labels): **Urgent** → **High** → **Medium** → **Low**. Prefer working Urgent/High in the active milestone before Medium/Low. Milestone tags: `milestone-1`, `milestone-2` (plus closed `milestone-0`).

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
