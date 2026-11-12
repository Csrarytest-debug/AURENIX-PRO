"""Conservative automatic cleanup of thin, loose strands in a rembg alpha mask.

The original RGB pixels are NEVER altered. This only removes foreground alpha
outside sufficiently substantial foreground regions. It is not semantic cable
recognition and cannot safely erase cables crossing a product or its labels.
No AI model is loaded here. OpenCV is imported only while processing.
"""

from PIL import Image


def remove_loose_wires(image: Image.Image) -> tuple[Image.Image, int]:
    """Return (cleaned RGBA image, number of removed foreground pixels).

    If segmentation has no substantial object, or too much would be removed,
    leave the image unchanged rather than damage the product. All image data
    remains in memory; the caller owns file saving and undo/editing.
    """
    if image.mode != 'RGBA':
        raise ValueError('Wire cleanup expects an RGBA segmentation result')
    import cv2
    import numpy as np

    alpha = np.asarray(image.getchannel('A'))
    height, width = alpha.shape
    if min(height, width) < 96:
        return image, 0

    foreground = (alpha >= 24).astype(np.uint8) * 255
    foreground_count = int(cv2.countNonZero(foreground))
    if foreground_count < 100:
        return image, 0

    # A thin cable disappears under opening; the substantial equipment body
    # remains. Kernel scales with image size, not the selected export DPI.
    diameter = min(21, max(5, round(min(height, width) * 0.008)))
    if diameter % 2 == 0:
        diameter += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (diameter, diameter))
    thick_regions = cv2.morphologyEx(foreground, cv2.MORPH_OPEN, kernel)

    # Keep multiple separate objects (e.g. camera and power supply), not just
    # the largest component. Tiny residual islands are excluded.
    n, labels, stats, _ = cv2.connectedComponentsWithStats(thick_regions, 8)
    min_core_area = max(30, int(foreground_count * 0.0004))
    valid = np.zeros(n, dtype=np.uint8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_core_area:
            valid[i] = 255
    valid[0] = 0
    core = valid[labels]
    if not np.any(core):
        return image, 0

    # Restore original anti-aliased outlines around thick product regions,
    # protecting mounting ears, labels, ports and normal edge details.
    margin = max(3, diameter // 2)
    protect = cv2.dilate(core, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (2 * margin + 1, 2 * margin + 1)))
    keep = (protect != 0)
    removed = int(np.count_nonzero((foreground != 0) & ~keep))
    if removed == 0 or removed > foreground_count * 0.18:
        return image, 0

    # No RGB inpainting: removed wires reveal the chosen pure-white/custom/
    # transparent background during the existing alpha compositing step.
    cleaned_alpha = alpha.copy()
    cleaned_alpha[~keep] = 0
    cleaned = image.copy()
    cleaned.putalpha(Image.fromarray(cleaned_alpha, 'L'))
    return cleaned, removed
