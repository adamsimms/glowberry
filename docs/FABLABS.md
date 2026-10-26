# Montreal fab labs for small test prints

Shortlist of Montreal-area fab labs for the desk test prints of small glowberries ([#61](https://github.com/adamsimms/glowberry/issues/61)): the labelled v17 test set in `models/print/ready_v17/` described in [`SCANNING.md`](SCANNING.md). Not for the 6 ft shell, which stays with Artefact ([`BRIEF.md`](BRIEF.md)). Picking and trying a lab is tracked in [#68](https://github.com/adamsimms/glowberry/issues/68).

Checked 2026-10-24 against each lab's own site where one exists, plus the [Fab Labs Québec wiki](https://wiki.fablabs.quebec/) for machine lists. Many fablabs.io entries are years out of date. Prices, hours, and machines change, so confirm by email before going.

---

## What the tests need

- **Resin printer** for the 100 mm hollow `skin_35` berry and the 25 mm true-size berry. The skin texture is about ±0.025 mm, near the resin limit; FDM cannot show it.
- **FDM printer** for the 2 in plain berry and the 100 mm `skin_fdm_min` berry.
- **Orange or amber material** ([`MATERIALS.md`](MATERIALS.md)). Lab stock is mostly grey, white, or black resin and plain PLA, so ask whether you can bring a translucent orange resin or amber filament. Formlabs printers have an open-material mode and Elegoo printers take third-party resin, but each lab sets its own rule.
- **Build volume** for the 100 mm berry: 109 x 114 x 100 mm. Tilted for supports along the plate's long side, the 109 mm side has to fit the plate's short side (123 to 125 mm on the Form 4 and Saturn 3 Ultra).
- **Resin per print:** about 79 mL for a hollow 100 mm berry (1.5 to 3 mm wall), plus supports.

---

## Shortlist

### 1. PolyFab Normand Brais (Polytechnique Montréal): best resin fleet

- **Machines:** three Formlabs Form 4 and one Elegoo Saturn 3 Ultra (10 µm minimum layer), with Form Wash, Form Cure, and an ultrasonic cleaner ([PolyFab SLA page](https://polyfab.polymtl.ca/technologies-offertes/impression-3d-sla/)). The wiki also lists a Form 3 and Form 3B. FDM: Bambu Lab X1-Carbon, Bambu Lab H2D, Ultimaker S5 and 3.
- **Access:** open to external members ([tarifs](https://polyfab.polymtl.ca/commencer-ici/)): $15 for one week, $25 for 15 days, $50 per month. Requires photo ID, the health and safety training, and a booking in Polysafe. No working alone. Open weekdays, closed weekends.
- **Cost:** machine time is free; resin is billed per mL, failed prints included. Standard grey, white, black $0.35; clear, tough, durable $0.40; Elegoo grey water-washable $0.09. A hollow 100 mm berry in clear is roughly $32 before supports.
- **Why first:** the Form 4 and Saturn 3 Ultra are the best chance of resolving the skin. A one-week pass covers a print, review, and reprint cycle, and the FDM files can run the same week.
- **Ask:** whether open-material mode or own resin is allowed (grey is out for these tests).
- **Where:** Pavillons Lassonde, Université-de-Montréal metro. polyfab@polymtl.ca, 514-340-4711 ext. 2233.

### 2. Fab Lab Brossard (Brossard library): easiest access, both printer types

- **Machines** ([equipment page](https://biblio.brossard.ca/fablab/machines-et-outils-de-fabrication/)): Bambu Lab X1-Carbon and a second filament printer (PLA), Formlabs Form 3 (SLA). Also a thermoformer and a 3D scanner.
- **Access:** free for everyone; materials are paid ([tarification](https://biblio.brossard.ca/fablab/tarification/)). Library members get reduced rates (non-member rates run about three times higher in the published grid). Non-residents can join for $110 per year. Open Thursday 16:00 to 21:00, Friday 12:00 to 21:00, Saturday and Sunday 12:00 to 17:00; closed Monday to Wednesday.
- **Why:** evening and weekend hours, staff who teach the machines, no training gate before a first visit.
- **Ask:** whether the Form 3 is running (the wiki lists their older Form 2 as temporarily out of service), the 3D printing rates in the [current grid](https://biblio.brossard.ca/fablab/wp-content/uploads/tarifs/grille_tarifaire_fablab.pdf), and whether PETG or own filament is allowed (PLA is the only filament named).
- **Where:** 7855 avenue San-Francisco, Brossard (South Shore). fablab@brossard.ca, 450-923-6350 ext. 6262.

### 3. InterFAB (Bibliothèque interculturelle, Côte-des-Neiges): library lab with resin

- **Machines** ([wiki](https://wiki.fablabs.quebec/index.php/InterFAB)): Ultimaker 3 (FDM), Formlabs Form 3 (SLA). The [city page](https://montreal.ca/lieux/bibliotheque-interculturelle) confirms 3D printers without naming models. A Fab Academy graduate is on staff for project advice.
- **Access:** Montreal library network. InterFAB hours: Monday 10:00 to 18:00, Tuesday and Wednesday 12:00 to 18:00, Thursday and Friday 10:00 to 17:30, Saturday and Sunday 10:00 to 16:30. 3D printing prices are not published on the pages checked.
- **Why:** on the island, open seven days, one resin and one FDM printer.
- **Ask:** pricing, queue length, and own material. The Ultimaker 3 takes 2.85 mm filament, so bring-your-own amber filament has to match.
- **Where:** 6767 chemin de la Côte-des-Neiges, 3rd floor. bicfablab@gmail.com, 514-868-7612.

### 4. échofab (Communautique, District Central): most machines, membership first

- **Machines:** Elegoo Mars 3 Pro and Saturn 2 8K resin printers, reservable with a subscription ([échofab](https://www.echofab.quebec/en/equipements/imprimante-3d-a-resine-dlp/)). The wiki adds a Form 3B, five Prusa i3 MK3 at $0.50 per gram, a BigRep Studio large-format printer, a thermoformer, and 3D scanners.
- **Access:** subscription required to reserve machines; price not published on the pages checked. A local news article from about 2021 describes free Thursdays for non-members; not confirmed for now.
- **Why:** several open resin printers (easiest place to run own tinted resin), and the BigRep is relevant later for mid-size lit tests.
- **Where:** 55 rue de Louvain Ouest, suite 330 (Ahuntsic). info@communautique.quebec, 514-948-6644.

**If only one:** PolyFab on a one-week pass. **If hours or cost matter more than resin quality:** Brossard.

---

## Commercial print services (send files, they print)

Checked 2026-10-26 against each service's own site. For the v17 set (prints 1 to 8 in [`SCANNING.md`](SCANNING.md)), resin and FDM are easy to source; full colour (6 to 8) is not confirmed anywhere in Montreal.

| Service | Resin | FDM | Full colour | Notes |
|---|---|---|---|---|
| [Fablab Inc.](https://fablabinc.com/en/professional-3d-printing-service/), 160 rue Saint-Viateur Est | SLA (14.5 x 17.5 x 14.5 cm) | Yes | PolyJet listed, "contact us"; colour not stated | Online upload and instant price, ships. info@fablabinc.com, 514-779-1309 |
| [MatterThings](https://www.matterthings.com/), Pincourt | SLA | Yes | PolyJet listed; colour not stated | Quote by email. 3d@matterthings.com, 514-312-6060 |
| [Axis Prototypes](https://www.axisproto.com/), 6956 rue Jarry Est | SLA | Yes | No PolyJet | Send, quote, build, deliver |
| [3DCentral](https://3dcentral.ca/3d-printing-service/), Laval | No | PLA, PETG | Up to four filament colours, not a gradient | Upload STL, 3MF, OBJ up to 60 MB |

Full colour outside Montreal: [Xometry](https://www.xometry.com/capabilities/3d-printing-service/polyjet-3d/) prints full-colour PolyJet from 3MF (Canadian shipping not confirmed); [Custom Prototypes](https://customprototypes.ca/services/polyjet-3d-printing/), Toronto, has a Mimaki with a 76 mm build height, so it fits prints 7 and 8 but not the 100 mm berry.

Ask: whether the PolyJet is a full-colour J-series that reads per-vertex colour 3MF; whether resin can be clear or translucent amber (the varying wall needs light through it); keep supports off the number; rinse the inside through the 10 mm hole; a quote and lead time for all eight.

---

## Not shortlisted

| Lab | Reason |
|-----|--------|
| [Fab Lab du PEC](https://fablabdupec.com/creer/machines-et-outils/) | Official page lists only FDM PLA printers (DittoPro, Ender 3) at $5/h for two hours, then $2.50/h. A Form 1+ appears only in an old wiki entry. $30 per year, Tuesday to Friday 11:00 to 15:00. Moved to 4650 rue Ontario Est. Cheap FDM fallback. |
| District 3 (Concordia) | Incubator makerspace for its own startups. Makerspace page returned an error on 2026-10-24. |
| LCC Fab Lab | Private K-12 school. Professionals by appointment or invite, in exchange for teaching time. |
| L'Architech (Collège de Montréal) | Private school lab for its students. |
| FabLab CSMB (formerly @Marguerite) | Network of high-school labs for students. |
| Fablab@Champlain | Listed as planned; college community first. |
| MontreaLab | Closed; transferred to Lespacemaker. |
| La Fabrique (Sherbrooke) | Closed. |

Two montreal.ca event links were also checked. "Samedis créatifs" is a craft session for children 6 to 12 at the Bibliothèque interculturelle (home of InterFAB), not fab lab access. "Le télescope James Webb" is a science talk at the Notre-Dame-de-Grâce library.

---

## Mayku FormBox

A desktop vacuum former, not a lab. It could pull a thin clear or tinted sheet over a printed berry to make a lit shell for light tests. A round berry has undercuts, so it would take two half-shells. Brossard and échofab both have thermoformers, so try one there before buying.
