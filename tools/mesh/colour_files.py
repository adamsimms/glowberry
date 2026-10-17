# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["trimesh", "numpy", "scipy", "networkx", "pymeshlab"]
# ///
"""Colour files for full-colour printing (PolyJet, Mimaki, MJF Color).

STL carries no colour, so these write 3MF with a per-vertex colour group
(3MF materials extension), plus a zipped VRML with vertex colours for the
gradient files, since some services prefer it.

- gradient: designed, even blend from amber at the top to deeper orange at
  the base. Not taken from the scan.
- amber / orange: one flat colour, for solid-colour comparison prints.

Translucency is not in the file; ask the service for colour-tinted
translucent (PolyJet VeroVivid) or opaque when ordering.

Writes models/print/colour/.

Run:
    uv run tools/mesh/colour_files.py
"""

import os
import zipfile

import numpy as np
import pymeshlab as ml
import trimesh

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "models", "print")
OUT_DIR = os.path.join(SRC, "colour")

AMBER = (255, 176, 46)   # #FFB02E
ORANGE = (232, 106, 23)  # #E86A17
GRADIENT_STEPS = 64

SOURCES = {
    "skin35_100mm_hollow": os.path.join(SRC, "ready", "resin_skin35_100mm.stl"),
    "plain_2in": os.path.join(SRC, "berry_seams_wander_50_w50.8mm.stl"),
    "plain_25mm": os.path.join(SRC, "ready", "resin_plain_true_size_25mm.stl"),
}


def gradient_colours(m):
    z = m.vertices[:, 2]
    t = (z - z.min()) / np.ptp(z)
    t = t * t * (3 - 2 * t)  # ease, so the ends hold their colour
    t = np.round(t * (GRADIENT_STEPS - 1)) / (GRADIENT_STEPS - 1)
    c = (1 - t)[:, None] * np.array(ORANGE) + t[:, None] * np.array(AMBER)
    return np.round(c).astype(np.uint8)


def write_3mf(path, m, colours):
    """3MF core + materials colorgroup, one colour index per vertex."""
    palette, idx = np.unique(colours, axis=0, return_inverse=True)
    idx = idx.ravel()
    hexes = "".join(f'<m:color color="#{r:02X}{g:02X}{b:02X}"/>' for r, g, b in palette)
    V, F = m.vertices, m.faces
    verts = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in V)
    P = idx[F]
    tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}" pid="1" p1="{p}" p2="{q}" p3="{r}"/>'
                   for (a, b, c), (p, q, r) in zip(F, P))
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02">'
        f'<resources><m:colorgroup id="1">{hexes}</m:colorgroup>'
        f'<object id="2" type="model" pid="1" pindex="{idx[0]}"><mesh>'
        f'<vertices>{verts}</vertices><triangles>{tris}</triangles>'
        '</mesh></object></resources><build><item objectid="2"/></build></model>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
        '</Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
        'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
        '</Relationships>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    return len(palette)


def write_vrml_zip(path, m, colours):
    ms = ml.MeshSet()
    rgba = np.hstack([colours / 255.0, np.ones((len(colours), 1))])
    ms.add_mesh(ml.Mesh(m.vertices, m.faces, v_color_matrix=rgba))
    wrl = path[:-len(".zip")]
    ms.save_current_mesh(wrl, save_vertex_color=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(wrl, os.path.basename(wrl))
    os.remove(wrl)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, src in SOURCES.items():
        m = trimesh.load(src)
        g = gradient_colours(m)
        n = write_3mf(os.path.join(OUT_DIR, f"gradient_{name}.3mf"), m, g)
        write_vrml_zip(os.path.join(OUT_DIR, f"gradient_{name}.wrl.zip"), m, g)
        print(f"gradient_{name}: {len(m.faces)} faces, {n} colours")
        for label, rgb in (("amber", AMBER), ("orange", ORANGE)):
            solid = np.tile(np.array(rgb, np.uint8), (len(m.vertices), 1))
            write_3mf(os.path.join(OUT_DIR, f"solid_{label}_{name}.3mf"), m, solid)
            print(f"solid_{label}_{name}: done")


if __name__ == "__main__":
    main()
