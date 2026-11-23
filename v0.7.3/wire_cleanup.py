"""Conservative, per-photo cable handling for AURENIX V0.7.3.

This is NOT semantic cable detection or inpainting. Connected foreground,
including equipment wiring, remains protected; isolated thin background
strands may be removed. Upstream rembg can still mis-segment fine wires.
"""
from pathlib import Path
import re

from PIL import Image

_AJA_ADAPTER_SAMPLES = re.compile(r"^img_(?:5712|5703)(?:$|[^0-9])", re.IGNORECASE)


def is_known_aja_sample(path):
    """Exact user-provided AJA kit photo IDs; not general visual recognition."""
    return bool(path and _AJA_ADAPTER_SAMPLES.match(Path(str(path)).stem))


def choose_wire_policy(image_path, overrides=None):
    """Resolve policy for ONE photo. Known AJA samples always retain leads."""
    if is_known_aja_sample(image_path):
        return "preserve_all"
    if not image_path:
        return "selective"
    choice = (overrides or {}).get(str(image_path), "selective")
    if choice not in ("selective", "preserve_all"):
        raise ValueError("Unknown per-photo cable policy")
    return choice


def remove_loose_wires(image: Image.Image, *, mode="selective") -> tuple[Image.Image, int]:
    """Trim only detached thin strands; preserve device-connected components.

    preserve_all: skip mask trimming (adapter kit). This cannot recover wires
    that the earlier segmentation stage has excluded from the foreground.
    """
    if image.mode != "RGBA":
        raise ValueError("Wire cleanup expects an RGBA segmentation result")
    if mode not in ("selective", "preserve_all"):
        raise ValueError("Unknown per-photo cable policy")
    if mode == "preserve_all":
        return image, 0

    import cv2
    import numpy as np

    alpha = np.asarray(image.getchannel("A"))
    height, width = alpha.shape
    if min(height, width) < 96:
        return image, 0

    foreground = (alpha >= 24).astype(np.uint8) * 255
    fg_count = int(cv2.countNonZero(foreground))
    if fg_count < 100:
        return image, 0

    diameter = min(21, max(5, round(min(height, width) * 0.008)))
    if diameter % 2 == 0:
        diameter += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (diameter, diameter))
    thick = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel)
    n_core, core_labels, core_stats, _ = cv2.connectedComponentsWithStats(thick, 8)
    core_valid = np.zeros(n_core, dtype=np.uint8)
    area_min = max(30, int(fg_count * 0.0004))
    for idx in range(1, n_core):
        if core_stats[idx, cv2.CC_STAT_AREA] >= area_min:
            core_valid[idx] = 1
    core_valid[0] = 0
    core = core_valid[core_labels] != 0
    if not np.any(core):
        return image, 0

    # Components of the ORIGINAL foreground are protected when they connect
    # to a substantial equipment core, including all attached cable strands.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    protected = np.zeros(count, dtype=np.bool_)
    protected[np.unique(labels[(foreground != 0) & core])] = True
    protected[0] = False

    # An isolated, long, thin strand is a candidate for background cleanup.
    # Short connectors, antennas, labels and free-standing equipment stay.
    for idx in range(1, count):
        if protected[idx]:
            continue
        w = int(stats[idx, cv2.CC_STAT_WIDTH])
        h = int(stats[idx, cv2.CC_STAT_HEIGHT])
        area = int(stats[idx, cv2.CC_STAT_AREA])
        long = max(w, h) >= max(25, diameter * 4)
        thin = min(w, h) <= max(6, diameter * 2)
        sparse = area / max(1, w * h) < 0.20
        if not long or not (thin or sparse):
            protected[idx] = True

    keep = protected[labels]
    # Restore 1px anti-aliasing fringe around retained foreground components.
    keep = cv2.dilate(keep.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0
    removed = int(np.count_nonzero((foreground != 0) & ~keep))
    if removed == 0 or removed > fg_count * 0.18:
        return image, 0
    adjusted = alpha.copy()
    adjusted[~keep] = 0
    cleaned = image.copy()
    cleaned.putalpha(Image.fromarray(adjusted, "L"))
    return cleaned, removed
