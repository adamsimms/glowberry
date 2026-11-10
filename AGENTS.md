# Agent notes

Glowberry, developed in the open. One milestone or one issue per chat when the work is mechanical.

## Hard rules

- Do **not** invent site permissions, landowner agreements, fabricator quotes, or funding commitments. No site outreach is sent before the pitch package exists.
- Do **not** commit moodboards, location photos, Blender/STL/OBJ/3MF files, renders or other large binaries; they go to the project's media folder. The provenance scan (`models/provenance/`) is the one tracked binary.
- Controller path is ESP32/Arduino-class, not Raspberry Pi, for the v1 heartbeat.
- No phase dates in `docs/`; dates live on issues.
- Dual license: docs/creative CC BY-NC 4.0, software MIT ([LICENSE.md](LICENSE.md)).
- Never use the word "master" in new user-facing text, docs, comments, or identifiers.
- Secrets only via `.env`; see `.env.example`.

## Canonical docs

1. [docs/BRIEF.md](docs/BRIEF.md): the brief. Body is the current state; its decisions log is one dated line per change.
2. [docs/POWER.md](docs/POWER.md): light, battery, solar, controller
3. [docs/MATERIALS.md](docs/MATERIALS.md): print, coatings, translucency, mass bands
4. [docs/SCANNING.md](docs/SCANNING.md): photogrammetry of the provenance berry; mesh tools
5. [docs/FABLABS.md](docs/FABLABS.md), [docs/INFLATABLE.md](docs/INFLATABLE.md) (archived track), [docs/RESEARCH_sculpture_precedents.md](docs/RESEARCH_sculpture_precedents.md)

Docs policy and the decisions rule (work decision vs proposal choice vs option): [`.cursor/rules/docs.mdc`](.cursor/rules/docs.mdc).

## GitHub

Issues here are about the work. Applications, calls, residencies and their deadlines are tracked in the private studio repo, not here. Board: [Glowberry — R&D](https://github.com/users/adamsimms/projects/2). Issue titles have no kind prefix; kind and priority live on labels.

## Private material

Applications, organization and call records, the CV, contact details and private research notes live in the private repo **adamsimms/studio** (`~/Documents/GitHub/studio`; read its `AGENTS.md` first). This project's applications are `applications/<cycle>-<call>-glowberry/`. Nothing from studio comes into this repo unless an issue says so and Adam approved it. Never put a phone number or home address here, including inside PDFs; a global pre-commit guard blocks text.

## Project media

Media (meshes, print files, renders, maquettes, visual tests, photos, video) never stays in this repo's ignored folders: they are not backed up. It goes to the project's synced Drive folder, `$MEDIA_DIR` (`30 STUDIO/32 PROJECTS/GLOWBERRY/`): `01 REFERENCES`, `02 STUDIES` (concept and visual exploration), `03 TESTS` (technical experiments, test prints), `04 ARTWORK` (the finished work's own media), `05 DOCUMENTATION` (one folder per activity, named like studio's). Inside 02 and 03, one dated folder per piece of work: `<YYYY-MM> <name>`. `sketchpad/` is scratch.

## Bibliography / Zotero

Zotero is the source library (public library, Glowberry collection `3Z9ZID5J`). `docs/BIBLIOGRAPHY.md` is generated: `node ~/Documents/GitHub/studio/scripts/zotero/build-bibliography.mjs glowberry --out docs/BIBLIOGRAPHY.md`; never edit it by hand. Writing to Zotero is publishing: only approved batches. Never query `~/Zotero/zotero.sqlite`. Do not invent citations.

## Support

No funder support to acknowledge yet. When an award lands, add the funder and its acknowledgement wording here and in the README.
