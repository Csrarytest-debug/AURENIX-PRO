"""Fail-safe, per-image wiring policies for AURENIX PRO V0.7.3.

The current AI segmenter is NOT a semantic cable detector. This module can
remove only detached thin foreground-mask components. Hardware/attached leads
must remain protected; uncertain wires are retained for human review.

The upstream background segmenter may omit wires before this module runs.
None of the policies can reconstruct missing cables or remove wires that
cross opaque equipment surfaces. Real photo QC is a separate release gate.
"""
from pathlib import Path
import re

from PIL import Image

POLICIES = ("auto_context", "remove_stray", "keep_attached", "keep_all")

# These sample IDs are grounded user-provided references, NOT vision inference.
_AJA_SAMPLES = re.compile(r"^img_(?:5712|5703)(?:$|[^0-9])", re.IGNORECASE)
_CAMERA_RACK_SAMPLES = re.compile(
    r"^img_(?:5801|5782|5696)(?:$|[^0-9])", re.IGNORECASE
)


def is_known_aja_sample(path):
    return bool(path and _AJA_SAMPLES.match(Path(str(path)).stem))


def get_requested_policy(image_path, overrides=None):
    """User's explicit per-image choice; auto_context if not overridden."""
    if not image_path:
        return "auto_context"
    chosen = (overrides or {}).get(str(image_path), "auto_context")
    if chosen not in POLICIES:
        raise ValueError("Invalid cable policy for this input image")
    return chosen


def choose_wire_policy(image_path, overrides=None):
    """Resolve an effective processing mode for the EXACT input file path.

    Manual overrides always win, including on recognized AJA sample photos.
    Auto Context is intentionally a conservative filename/reference fallback:
      - IMG_5712 / IMG_5703: keep attached/nearby power-adapter cables
      - known camera/rack sample IDs: remove detached stray mask components
      - unrecognized photos: keep attached/nearby strands (fail-safe)
    No image-content/semantic classification is implied by this behavior.
    """
    requested = get_requested_policy(image_path, overrides)
    if requested != "auto_context":
        return requested
    if is_known_aja_sample(image_path):
        return "keep_attached"
    if image_path and _CAMERA_RACK_SAMPLES.match(Path(str(image_path)).stem):
        return "remove_stray"
    return "keep_attached"


def remove_loose_wires(image: Image.Image, *, mode="remove_stray") -> tuple[Image.Image, int]:
    """Return (RGBA, pixel_count_removed) without altering retained RGB.

    remove_stray: trim only narrow DETACHED foreground alpha components.
    keep_attached: additionally retain cable-like components close to the
       equipment core (including coiled adapter leads separated in the mask).
    keep_all: do not change the segmented RGBA at all.
    """
    if image.mode != "RGBA":
        raise ValueError("Wire cleanup expects RGBA segmentation result")
    if mode not in ("remove_stray", "keep_attached", "keep_all"):
        raise ValueError("Unresolved or invalid cable policy")
    if mode == "keep_all":
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
    substantial = np.zeros(n_core, dtype=np.uint8)
    min_area = max(30, int(fg_count * 0.0004))
    for idx in range(1, n_core):
        if core_stats[idx, cv2.CC_STAT_AREA] >= min_area:
            substantial[idx] = 1
    substantial[0] = 0
    core = substantial[core_labels] != 0
    if not np.any(core):
        return image, 0

    # Protect COMPLETE ORIGINAL components touching any equipment core.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground, 8)
    keep_component = np.zeros(count, dtype=np.bool_)
    anchored = np.unique(labels[(foreground != 0) & core])
    keep_component[anchored] = True
    keep_component[0] = False

    # For adapter kits, retain near-equipment thin components as well. Coiled
    # power leads can be separated by segmentation and must not disappear.
    if mode == "keep_attached":
        # Distance transform avoids a huge 25%-image-size morphology
        # kernel that could stall Windows or spike RAM on large batches.
        protect_radius = max(16, round(min(height, width) * .25))
        protect_near = cv2.distanceTransform(
            (~core).astype(np.uint8), cv2.DIST_L2, 3
        ) <= protect_radius
        near_ids = np.unique(labels[protect_near & (foreground != 0)])
        keep_component[near_ids] = True
        keep_component[0] = False

    # Never erase small detached connectors/antennas or complete product bodies.
    # Only REMOVE long/thin components with no protected anchor/proximity.
    for idx in range(1, count):
        if keep_component[idx]:
            continue
        area = int(stats[idx, cv2.CC_STAT_AREA])
        w = int(stats[idx, cv2.CC_STAT_WIDTH])
        h = int(stats[idx, cv2.CC_STAT_HEIGHT])
        is_long = max(w, h) >= max(25, diameter * 4)
        is_thin = min(w, h) <= max(6, diameter * 2)
        is_sparse = area / max(1, w * h) < .20
        if not (is_long and (is_thin or is_sparse)):
            keep_component[idx] = True

    keep = keep_component[labels]
    # Keep antialiased fringe next to retained objects without RGB inpainting.
    keep = cv2.dilate(keep.astype(np.uint8), np.ones((3, 3), np.uint8)) != 0
    removed = int(np.count_nonzero((foreground != 0) & ~keep))
    if removed == 0 or removed > fg_count * .18:
        return image, 0

    new_alpha = alpha.copy()
    new_alpha[~keep] = 0
    cleaned = image.copy()
    cleaned.putalpha(Image.fromarray(new_alpha, "L"))
    return cleaned, removed
