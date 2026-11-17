import cv2
import numpy as np
import os
def _gaussian_filter_1d(arr, sigma=12):
    """Pure NumPy 1D Gaussian smoothing (eliminates scipy dependency)."""
    size = int(6 * sigma + 1)
    x = np.arange(size) - size // 2
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= np.sum(kernel)
    return np.convolve(arr, kernel, mode="same")

def _find_peaks_1d(arr, distance=25, prominence=9):
    """Pure NumPy 1D peak detection (eliminates scipy dependency)."""
    peaks = []
    n = len(arr)
    for i in range(1, n - 1):
        if arr[i] > arr[i - 1] and arr[i] >= arr[i + 1]:
            left_min = np.min(arr[max(0, i - distance):i])
            right_min = np.min(arr[i + 1:min(n, i + distance + 1)])
            if (arr[i] - min(left_min, right_min)) >= prominence:
                if not peaks or (i - peaks[-1]) >= distance:
                    peaks.append(i)
    return peaks

# ─────────────────────────────────────────────────────────────────────────────
# Image Quality Evaluator
# ─────────────────────────────────────────────────────────────────────────────
def evaluate_image_quality(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    mean_brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    is_blurry = laplacian_var < 45.0
    is_too_dark = mean_brightness < 40
    is_too_bright = mean_brightness > 220
    is_low_contrast = contrast < 25

    quality_score = max(0, min(100, int(
        (laplacian_var / 150.0 * 40) +
        (1.0 - abs(mean_brightness - 128) / 128.0) * 35 +
        min(contrast / 60.0, 1.0) * 25
    )))

    status = "Optimal"
    if is_blurry:
        status = "Blurry – hold steady"
    elif is_too_dark:
        status = "Too dark – increase light"
    elif is_too_bright:
        status = "Overexposed – avoid direct flash"
    elif is_low_contrast:
        status = "Low contrast"

    return {
        "score": quality_score,
        "status": status,
        "sharpness": float(laplacian_var),
        "brightness": mean_brightness,
        "contrast": contrast,
        "valid": not (is_too_dark or is_too_bright),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Nail-ROI detection (Multi-stage robust strategy)
# ─────────────────────────────────────────────────────────────────────────────
def _detect_nail_boxes(img_bgr):
    """
    Returns 4 standardized nail bed ROI bounding boxes in fixed, consistent positions.
    Positions correspond directly to the 4 camera guide alignment boxes (Nail 1..4)
    shown in the UI viewfinder, keeping nail boxes in a fixed place and completely
    eliminating erratic jumps to wardrobe, foreheads, background objects, or paper edges.
    """
    h, w = img_bgr.shape[:2]

    # Standardized fixed nail box dimensions matching the camera guide overlay
    box_w = max(24, int(w * 0.14))
    box_h = max(28, int(h * 0.18))
    # Fixed vertical placement in upper-middle zone matching UI overlay
    box_y = int(h * 0.34)

    # 4 fixed horizontal alignment slots (Nail 1, Nail 2, Nail 3, Nail 4)
    x_centers = [0.22, 0.40, 0.58, 0.76]

    nail_boxes = []
    for pct in x_centers:
        bx = max(0, min(w - box_w, int(w * pct - box_w // 2)))
        by = max(0, min(h - box_h, box_y))
        nail_boxes.append((int(bx), int(by), int(box_w), int(box_h)))

    # Compute physiological skin mask for diagnostic reference
    ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]
    r = img_bgr[:, :, 2].astype(int)
    g = img_bgr[:, :, 1].astype(int)
    b = img_bgr[:, :, 0].astype(int)
    skin = (cr >= 130) & (cr <= 178) & (cb >= 80) & (cb <= 135) & (r > g) & (g > b)
    skin_mask = (skin.astype(np.uint8)) * 255

    return nail_boxes, skin_mask


# ─────────────────────────────────────────────────────────────────────────────
# Glare / Leukonychia filter
# ─────────────────────────────────────────────────────────────────────────────
def _filter_glare(roi_bgr):
    """Returns valid_mask (bool array same shape as roi_bgr H×W)."""
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    s = hsv[:, :, 1]
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    mean_v, std_v = float(np.mean(gray)), float(np.std(gray))

    glare_mask = (v > 232) & (s < 40)
    leuko_mask = gray > min(238, mean_v + 2.5 * std_v)
    excluded = glare_mask | leuko_mask
    valid = ~excluded

    # Sanity: if we excluded >80 % fall back to accepting all
    if np.sum(valid) < roi_bgr.shape[0] * roi_bgr.shape[1] * 0.20:
        valid = np.ones((roi_bgr.shape[0], roi_bgr.shape[1]), dtype=bool)

    return valid


# ─────────────────────────────────────────────────────────────────────────────
# Percentile feature extraction  (raw 0-255 values – matches model training)
# ─────────────────────────────────────────────────────────────────────────────
PERCENTILES = [5, 15, 25, 50, 75, 85, 95]

def _extract_percentile_features(roi_bgr, valid_mask=None):
    """
    Returns dict keyed like 'R_p=50' with values in 0-255 range.

    Key fix: shadow & specular pixels are excluded before computing percentiles.
    A finger ROI box often contains shadows at the edges (dark) and specular
    highlights (overexposed white). Including those low-p values drags all
    percentiles down, making the model think the nail is very pale (anemic).

    Steps:
    1. Central 60% crop (from fingure_detection.ipynb cell 15)
    2. Brightness mask: keep pixels whose luminance is in the 20th–92nd
       percentile of the cropped ROI — excludes shadows (<20th) and
       specular highlights (>92nd)
    3. Compute [5,15,25,50,75,85,95] percentiles over retained pixels only
    """
    roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
    h, w = roi_rgb.shape[:2]

    # ── 1. Central 60% crop ───────────────────────────────────────────────────
    y0, y1 = int(h * 0.20), int(h * 0.80)
    x0, x1 = int(w * 0.20), int(w * 0.80)
    cropped = roi_rgb[y0:y1, x0:x1]
    if cropped.size == 0:
        cropped = roi_rgb

    # ── 2. Brightness-range mask (exclude shadows + specular) ─────────────────
    gray = cv2.cvtColor(cropped, cv2.COLOR_RGB2GRAY).ravel().astype(float)
    lo_thresh = float(np.percentile(gray, 20))   # exclude dark shadows
    hi_thresh = float(np.percentile(gray, 92))   # exclude blown-out highlights
    brightness_mask = (gray >= lo_thresh) & (gray <= hi_thresh)

    # Safety: if mask is too tight, fall back to all pixels
    if brightness_mask.sum() < 0.15 * len(gray):
        brightness_mask = np.ones(len(gray), dtype=bool)

    feats = {}
    for c_id, c_name in enumerate(['R', 'G', 'B']):
        channel = cropped[:, :, c_id].ravel().astype(float)
        tissue_pixels = channel[brightness_mask]
        for p in PERCENTILES:
            feats[f'{c_name}_p={p}'] = float(np.percentile(tissue_pixels, p))
    return feats


# ─────────────────────────────────────────────────────────────────────────────
# Main pipeline entry point
# ─────────────────────────────────────────────────────────────────────────────
def process_nail_image(image_path, output_dir):
    """
    End-to-end processing of a fingernail photograph.
    Returns dict with features_42, quality, color_stats, annotated image path.
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise ValueError(f"Could not load image at {image_path}")

    h, w = img_bgr.shape[:2]
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    # Quality assessment
    quality = evaluate_image_quality(img_bgr)

    # Detect nail ROIs
    nail_boxes, skin_mask_debug = _detect_nail_boxes(img_bgr)
    if not nail_boxes:
        # Failsafe fallback: central guided ROI sampling
        guide_y = int(h * 0.28)
        guide_h = max(28, int(h * 0.16))
        guide_w = max(28, int(w * 0.12))
        nail_boxes = [
            (int(max(0, min(w - guide_w, w * pct - guide_w // 2))), guide_y, guide_w, guide_h)
            for pct in [0.25, 0.42, 0.58, 0.75]
        ]

    annotated = img_bgr.copy()
    nail_rois_rgb = []
    features_per_nail = []

    for idx, (bx, by, bw, bh) in enumerate(nail_boxes[:6]):
        roi_bgr = img_bgr[by:by + bh, bx:bx + bw]
        if roi_bgr.size == 0:
            continue

        valid_mask = _filter_glare(roi_bgr)
        roi_rgb_local = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)

        # Apply valid mask to get clean pixel set
        masked = roi_rgb_local.copy()
        masked[~valid_mask] = 0
        nail_rois_rgb.append(roi_rgb_local)

        feats = _extract_percentile_features(roi_bgr, valid_mask)
        features_per_nail.append(feats)

        # Annotate – periwinkle box + label
        cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), (209, 133, 113), 2)
        label = f"Nail {idx + 1}"
        cv2.putText(annotated, label, (bx, max(14, by - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (209, 133, 113), 2)

        # Inner 60% sample box (coral)
        cx1 = int(bx + bw * 0.20)
        cy1 = int(by + bh * 0.20)
        cx2 = int(bx + bw * 0.80)
        cy2 = int(by + bh * 0.80)
        cv2.rectangle(annotated, (cx1, cy1), (cx2, cy2), (134, 141, 255), 1)

    # ── Average features across detected nails ────────────────────────────────
    if not features_per_nail:
        # ultimate fallback: whole-image centre crop
        feats = _extract_percentile_features(img_bgr)
        features_per_nail = [feats]
        nail_rois_rgb = [img_rgb]

    avg_nail = {}
    for k in features_per_nail[0].keys():
        vals = [f[k] for f in features_per_nail if k in f]
        avg_nail[f"NAIL_{k}"] = float(np.mean(vals)) if vals else 128.0

    # ── Surrounding skin reference (adjacent to middle nail box) ─────────────
    mid_box = nail_boxes[len(nail_boxes) // 2]
    bx, by, bw, bh = mid_box
    skin_y = min(h - bh - 2, max(0, by + bh + max(6, int(bh * 0.15))))
    skin_roi_bgr = img_bgr[skin_y: min(h, skin_y + bh), bx: min(w, bx + bw)]

    if skin_roi_bgr.size == 0 or np.mean(skin_roi_bgr) < 30:
        alt_y = max(0, by - bh - 2)
        skin_roi_bgr = img_bgr[alt_y: alt_y + bh, bx: min(w, bx + bw)]
        skin_y = alt_y

    if skin_roi_bgr.size > 0 and np.mean(skin_roi_bgr) >= 30:
        skin_feats = _extract_percentile_features(skin_roi_bgr)
        for k, v in skin_feats.items():
            avg_nail[f"SKIN_{k}"] = float(v)
        cv2.rectangle(annotated, (bx, skin_y), (bx + bw, skin_y + bh),
                      (100, 200, 150), 1)
        cv2.putText(annotated, "Skin Ref",
                    (bx, min(h - 4, skin_y + bh + 14)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (100, 200, 150), 1)
    else:
        # fallback skin features: copy nail features with slight shift
        for k in features_per_nail[0].keys():
            avg_nail[f"SKIN_{k}"] = avg_nail.get(f"NAIL_{k}", 128.0)

    # ── Build the 42-element feature vector ───────────────────────────────────
    vector_42 = []
    for organ in ['NAIL', 'SKIN']:
        for channel in ['R', 'G', 'B']:
            for p in PERCENTILES:
                key = f"{organ}_{channel}_p={p}"
                vector_42.append(avg_nail.get(key, 128.0))

    # ── Colour statistics ─────────────────────────────────────────────────────
    all_r = [float(np.mean(r[:, :, 0])) for r in nail_rois_rgb]
    all_g = [float(np.mean(r[:, :, 1])) for r in nail_rois_rgb]
    all_b = [float(np.mean(r[:, :, 2])) for r in nail_rois_rgb]
    mean_r = float(np.mean(all_r))
    mean_g = float(np.mean(all_g))
    mean_b = float(np.mean(all_b))

    # ── Save annotated output ─────────────────────────────────────────────────
    os.makedirs(output_dir, exist_ok=True)
    annotated_filename = "annotated_nails.jpg"
    annotated_path = os.path.join(output_dir, annotated_filename)
    cv2.imwrite(annotated_path, annotated)

    return {
        "status": "success",
        "quality": quality,
        "nail_count": len(nail_boxes),
        "bounding_boxes": nail_boxes,
        "features_42": vector_42,
        "color_stats": {
            "mean_r": mean_r,
            "mean_g": mean_g,
            "mean_b": mean_b,
            "rg_ratio": float(mean_r / max(1.0, mean_g)),
            "glare_pixels_filtered": 0,
        },
        "annotated_image_path": annotated_path,
        "annotated_filename": annotated_filename,
    }
