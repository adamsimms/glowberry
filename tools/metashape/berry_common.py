"""Shared helpers for the berry reconstruction scripts.

Metashape 2.3.x notes that matter here:
  - Chunk.importMasks / Chunk.exportMasks no longer exist. Import masks with
    generateMasks(masking_mode=MaskingModeFile); export via Tasks.ExportMasks
    or Camera.mask.image().save().
  - The MaskSource enum is gone; only MaskingMode remains.
  - The embedded Python (3.12) ships no numpy, so it is pip-installed into a
    user-packages directory that must be added to sys.path by hand.
"""

import os
import sys

BERRY = os.environ.get("BERRY_ROOT", "/Users/adamsimms/Desktop/BERRY")
WORK = os.path.join(BERRY, "metashape")
PROJECT = os.path.join(WORK, "berry04_three_chunks.psx")

# Remount label -> source folder
REMOUNTS = [
    ("upright", "TIFF-CHUNK-01"),
    ("inverted", "TIFF-CHUNK-02"),
    ("sideways", "TIFF-CHUNK-03"),
]

# Ring label -> subpath within a remount folder
RINGS = [
    ("40", "40"),
    ("15", "15"),
    ("m5", "-5"),
    ("m5_notargets", os.path.join("-5", "NO-TARGETS")),
]


def add_user_packages():
    """Put the pip-installed user-packages dir on sys.path (numpy lives there)."""
    base = os.path.expanduser(
        "~/Library/Application Support/Agisoft/Metashape Pro"
    )
    target = os.path.join(
        base, "user-packages-py{}{}".format(*sys.version_info[:2])
    )
    if os.path.isdir(target) and target not in sys.path:
        sys.path.insert(0, target)
    return target


def enable_gpu(Metashape):
    gpus = Metashape.app.enumGPUDevices()
    Metashape.app.gpu_mask = 2 ** len(gpus) - 1 if gpus else 0
    Metashape.app.cpu_enable = not gpus
    return [g.get("name") for g in gpus]


# Every intact frame is either 305,698,387 or 305,698,373 bytes (a 14-byte
# metadata difference). B_2254, B_2255 and B_2256 were originally truncated by
# an interrupted TIFF export; libtiff failed on them and detectMarkers aborted
# the whole run rather than skipping them. They have since been re-exported and
# now pass. The size guard stays as cheap insurance against a repeat.
MIN_VALID_BYTES = 300_000_000
KNOWN_CORRUPT = set()


def is_valid_photo(path):
    """False for the truncated TIFFs that libtiff cannot decode."""
    stem = os.path.splitext(os.path.basename(path))[0]
    if stem in KNOWN_CORRUPT:
        return False
    try:
        return os.path.getsize(path) >= MIN_VALID_BYTES
    except OSError:
        return False


def ring_photos(remount_dir, ring_sub, skip_invalid=True):
    """Sorted photo paths for one ring. Excludes the *_MASK.tiff empty plates."""
    d = os.path.join(BERRY, remount_dir, ring_sub)
    if not os.path.isdir(d):
        return []
    out = []
    for name in sorted(os.listdir(d)):
        low = name.lower()
        if not low.endswith((".tif", ".tiff")):
            continue
        if "_mask." in low:  # empty plate, never a camera
            continue
        p = os.path.join(d, name)
        if skip_invalid and not is_valid_photo(p):
            continue
        out.append(p)
    return out


def all_rings():
    """Yield (remount_label, remount_dir, ring_label, ring_sub, photo_paths)."""
    for r_label, r_dir in REMOUNTS:
        for ring_label, ring_sub in RINGS:
            yield (
                r_label,
                r_dir,
                ring_label,
                ring_sub,
                ring_photos(r_dir, ring_sub),
            )


def ensure_dirs():
    for sub in ("masks", "overlays", "reports", "exports", "logs"):
        os.makedirs(os.path.join(WORK, sub), exist_ok=True)


def saturation(arr, np):
    """Per-pixel saturation in [0,1] from an HxWx3 uint8/float array."""
    a = arr[:, :, :3].astype(np.float32)
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)


def image_to_array(img, np, downscale=1):
    """Metashape.Image -> HxWx3 uint8 numpy array, optionally downscaled."""
    if downscale > 1:
        img = img.resize(img.width // downscale, img.height // downscale)
    rgb = img.convert("RGB", "U8")
    buf = np.frombuffer(rgb.tostring(), dtype=np.uint8)
    return buf.reshape(rgb.height, rgb.width, 3)


def hue_deg(arr, np):
    """Per-pixel HSV hue in degrees [0,360) from an HxWx3 array."""
    a = arr[:, :, :3].astype(np.float32)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    d = mx - mn
    safe = np.maximum(d, 1e-6)
    h = np.zeros_like(mx)
    is_r = (mx == r) & (d > 0)
    is_g = (mx == g) & (d > 0)
    is_b = (mx == b) & (d > 0)
    h[is_r] = (60.0 * ((g[is_r] - b[is_r]) / safe[is_r])) % 360.0
    h[is_g] = 60.0 * ((b[is_g] - r[is_g]) / safe[is_g]) + 120.0
    h[is_b] = 60.0 * ((r[is_b] - g[is_b]) / safe[is_b]) + 240.0
    return h


# The berry is orange/amber. The violet fringe along the paper edge in the
# low-angle rings is the only other saturated thing in the scene, and it sits
# near hue 270. Gating on hue as well as saturation separates them cleanly.
BERRY_SAT = 0.35
BERRY_HUE_LO = 335.0  # wraps through 0
BERRY_HUE_HI = 65.0


def berry_pixels(arr, np, sat_thr=BERRY_SAT, hue_lo=BERRY_HUE_LO, hue_hi=BERRY_HUE_HI):
    """Boolean mask of saturated, orange-hued pixels."""
    sat = saturation(arr, np)
    hue = hue_deg(arr, np)
    if hue_lo > hue_hi:  # wrapped range, e.g. 335..65
        in_hue = (hue >= hue_lo) | (hue <= hue_hi)
    else:
        in_hue = (hue >= hue_lo) & (hue <= hue_hi)
    return (sat > sat_thr) & in_hue


def largest_component(mask, np, max_labels=4096):
    """Largest 8-connected component of a boolean mask, via union-find.

    Cheap at downscaled sizes; used to locate the berry before refining the
    mask at full resolution inside its bounding box.
    """
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    parent = [0]

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    ys, xs = np.nonzero(mask)
    for y, x in zip(ys.tolist(), xs.tolist()):
        neigh = []
        for dy, dx in ((-1, -1), (-1, 0), (-1, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and labels[ny, nx]:
                neigh.append(labels[ny, nx])
        if not neigh:
            parent.append(len(parent))
            labels[y, x] = len(parent) - 1
        else:
            m = min(neigh)
            labels[y, x] = m
            for n in neigh:
                union(m, n)

    if len(parent) <= 1:
        return None, labels

    flat = np.zeros(len(parent), dtype=np.int32)
    for i in range(1, len(parent)):
        flat[i] = find(i)
    resolved = flat[labels]
    ids, counts = np.unique(resolved[resolved > 0], return_counts=True)
    if ids.size == 0:
        return None, resolved
    best = ids[int(np.argmax(counts))]
    return resolved == best, resolved
