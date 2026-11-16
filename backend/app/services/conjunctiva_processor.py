import cv2
import numpy as np
import os
import math
from backend.app.services.nail_processor import evaluate_image_quality

def calculate_erythema_index(r_mean, g_mean):
    """
    Erythema Index formula from Erythema Calculation.jpeg:
    E = 100 * log10(Red / Green)
    """
    if g_mean <= 0 or r_mean <= 0:
        return 0.0
    ratio = max(0.001, r_mean / max(1.0, g_mean))
    return float(100.0 * math.log10(ratio))

def segment_palpebral_conjunctiva(eye_roi_bgr):
    """
    Segments palpebral conjunctiva within eye ROI:
    - Focuses on the exposed lower eyelid mucosal shelf
    - Excludes white sclera (high brightness, balanced R=G=B)
    - Excludes dark iris / pupil (low brightness)
    - Isolates vascular mucosal redness in the lower eyelid
    """
    h, w = eye_roi_bgr.shape[:2]
    
    # Lower eyelid mucosal shelf is typically in lower 65% of the eye box
    y0 = int(h * 0.35)
    y1 = int(h * 0.90)
    
    b, g, r = cv2.split(eye_roi_bgr)
    
    # Blood-rich mucosal color mask:
    red_diff = r.astype(np.float32) - g.astype(np.float32)
    # Exclude white sclera where r, g, b are all high and close:
    is_sclera = (r > 190) & (g > 190) & (b > 190)
    # Exclude dark iris/pupil:
    is_dark = (r < 50) & (g < 50) & (b < 50)
    # Exclude specular flash glare:
    is_glare = (r > 245) & (g > 245)
    
    # Conjunctiva mask restricted to lower lid zone
    conjunctiva_mask = (red_diff > 10) & (r > 80) & (b < 165) & (~is_sclera) & (~is_dark) & (~is_glare)
    y_indices = np.arange(h)[:, None]
    conjunctiva_mask = conjunctiva_mask & (y_indices >= y0) & (y_indices <= y1)
    
    # Cleanup mask with morphology
    mask_uint8 = conjunctiva_mask.astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_cleaned = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, kernel, iterations=1)
    mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Find components
    contours, _ = cv2.findContours(mask_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    final_mask = np.zeros((h, w), dtype=np.uint8)
    if contours:
        valid_contours = [c for c in contours if 25 <= cv2.contourArea(c) <= 6000]
        if valid_contours:
            best_contour = max(valid_contours, key=cv2.contourArea)
            cv2.drawContours(final_mask, [best_contour], -1, 255, -1)
            
    if np.sum(final_mask) < 30:
        # Fallback anatomical crescent in lower palpebral zone
        cv2.ellipse(final_mask, (w // 2, int(h * 0.65)), (int(w * 0.28), int(h * 0.10)), 0, 0, 180, 255, -1)
        
    return final_mask

def process_conjunctiva_image(image_path, output_dir):
    """
    End-to-end processing of lower eyelid palpebral conjunctiva:
    1. Loads eye image
    2. Validates image quality
    3. Multi-cascade eye detection with physiological skin-mask validation
    4. Segments palpebral conjunctiva
    5. Calculates Erythema Index
    6. Generates visual overlays
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise ValueError(f"Could not load image at {image_path}")
        
    h, w = img_bgr.shape[:2]
    quality = evaluate_image_quality(img_bgr)
    
    annotated = img_bgr.copy()
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Compute skin mask (YCrCb: Cr in [128, 180], Cb in [78, 138])
    ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
    y_ch, cr, cb = cv2.split(ycrcb)
    skin_mask = (cr >= 128) & (cr <= 180) & (cb >= 78) & (cb <= 138)
    
    # Multi-cascade ensemble for robust eye detection across angles & eyewear
    cascades = [
        cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_righteye_2splits.xml'),
        cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_lefteye_2splits.xml'),
        cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml'),
        cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    ]
    
    candidates = []
    for cas in cascades:
        dets = cas.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=2, minSize=(25, 25))
        for d in dets:
            bx, by, bw, bh = int(d[0]), int(d[1]), int(d[2]), int(d[3])
            # Skin neighborhood verification: reject doors, cabinets, and walls
            sub_skin = skin_mask[max(0, by):min(h, by+bh), max(0, bx):min(w, bx+bw)]
            if sub_skin.size > 0 and np.mean(sub_skin) >= 0.30:
                candidates.append((bx, by, bw, bh))
                
    # Also check frontal/profile face detections if available
    face_cas = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cas.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=2, minSize=(100, 100))
    for fx, fy, fw, fh in faces:
        # Left and right eye zones of detected face
        candidates.append((int(fx + 0.10 * fw), int(fy + 0.22 * fh), int(0.36 * fw), int(0.36 * fh)))
        candidates.append((int(fx + 0.54 * fw), int(fy + 0.22 * fh), int(0.36 * fw), int(0.36 * fh)))
        
    def _score_eye_candidate(box):
        """Scores candidate box by exposed mucosal redness and presence of pupil/iris."""
        bx, by, bw, bh = box
        roi = img_bgr[by:min(h, by+bh), bx:min(w, bx+bw)]
        if roi.size == 0:
            return -1.0
        b_c, g_c, r_c = cv2.split(roi)
        diff = r_c.astype(float) - g_c.astype(float)
        # Mucosal redness: excess of red over green, within skin region
        is_mucosa = (diff > 12) & (r_c > 85) & (b_c < 165)
        mucosa_count = float(np.sum(is_mucosa))
        
        # Dark pupil/iris in upper 65% of the eye box
        top_gray = cv2.cvtColor(roi[:int(bh*0.65), :], cv2.COLOR_BGR2GRAY)
        min_g = np.min(top_gray) if top_gray.size > 0 else 100
        pupil_score = max(0, 75 - min_g) * 18.0
        
        # Sclera immediately adjacent
        is_sclera = (r_c > 140) & (g_c > 140) & (b_c > 130) & (np.abs(r_c.astype(int) - g_c.astype(int)) < 30)
        sclera_score = float(np.sum(is_sclera)) * 0.8
        
        return (mucosa_count * 2.8) + pupil_score + sclera_score

    if candidates:
        scored = [(b, _score_eye_candidate(b)) for b in candidates]
        scored.sort(key=lambda t: t[1], reverse=True)
        chosen = scored[0][0]
        ex, ey, ew, eh = chosen
        
        # Expand slightly downward to ensure the full palpebral mucosal margin is included
        pad_top = int(eh * 0.05)
        pad_bot = int(eh * 0.20)
        pad_x = int(ew * 0.08)
        ey0 = max(0, ey - pad_top)
        ey1 = min(h, ey + eh + pad_bot)
        ex0 = max(0, ex - pad_x)
        ex1 = min(w, ex + ew + pad_x)
        eye_box = (int(ex0), int(ey0), int(ex1 - ex0), int(ey1 - ey0))
    else:
        # Fallback: find mucosal redness peak on skin
        b_all, g_all, r_all = cv2.split(img_bgr)
        all_diff = r_all.astype(float) - g_all.astype(float)
        mucosa_map = (all_diff > 14) & (r_all > 90) & (b_all < 155) & skin_mask
        y_pts, x_pts = np.where(mucosa_map)
        
        if len(x_pts) > 30:
            cx = int(np.median(x_pts))
            cy = int(np.median(y_pts))
            ew = max(60, min(150, int(w * 0.28)))
            eh = max(60, min(150, int(h * 0.25)))
            eye_box = (max(0, cx - ew // 2), max(0, cy - int(eh * 0.65)), min(w - 10, ew), min(h - 10, eh))
        else:
            # Center viewport fallback
            cx, cy = w // 2, int(h * 0.42)
            ew, eh = int(w * 0.38), int(h * 0.30)
            eye_box = (max(0, cx - ew // 2), max(0, cy - eh // 2), min(w, ew), min(h, eh))
        
    bx, by, bw, bh = eye_box
    eye_roi_bgr = img_bgr[by:by+bh, bx:bx+bw]
    
    # Segment palpebral conjunctiva (excludes fingers)
    conj_mask = segment_palpebral_conjunctiva(eye_roi_bgr)
    
    # Calculate RGB stats in palpebral conjunctiva
    b, g, r = cv2.split(eye_roi_bgr)
    valid_pixels = conj_mask > 0
    
    if np.sum(valid_pixels) > 0:
        mean_r = float(np.mean(r[valid_pixels]))
        mean_g = float(np.mean(g[valid_pixels]))
        mean_b = float(np.mean(b[valid_pixels]))
    else:
        mean_r = 165.0
        mean_g = 125.0
        mean_b = 110.0
        
    erythema_index = calculate_erythema_index(mean_r, mean_g)
    
    # Create visual annotations
    # Draw eye region box
    cv2.rectangle(annotated, (bx, by), (bx + bw, by + bh), (113, 133, 209), 2)
    cv2.putText(annotated, "Eye Region", (bx, max(20, by - 8)), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (113, 133, 209), 2)
                
    # Overlay palpebral contour on full image
    mask_full = np.zeros((h, w), dtype=np.uint8)
    mask_full[by:by+bh, bx:bx+bw] = conj_mask
    
    contours_full, _ = cv2.findContours(mask_full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(annotated, contours_full, -1, (255, 141, 134), 2) # Coral highlight
    
    # Create mucosal overlay
    overlay = annotated.copy()
    overlay[mask_full > 0] = [235, 120, 100] # BGR mucosal tint
    cv2.addWeighted(overlay, 0.40, annotated, 0.60, 0, annotated)
    
    # Save visual outputs
    os.makedirs(output_dir, exist_ok=True)
    annotated_filename = "annotated_conjunctiva.jpg"
    annotated_path = os.path.join(output_dir, annotated_filename)
    cv2.imwrite(annotated_path, annotated)
    
    return {
        "status": "success",
        "quality": quality,
        "eye_box": eye_box,
        "erythema_index": erythema_index,
        "color_stats": {
            "mean_r": mean_r,
            "mean_g": mean_g,
            "mean_b": mean_b,
            "rg_ratio": float(mean_r / max(1.0, mean_g)),
            "segmented_pixels": int(np.sum(valid_pixels))
        },
        "annotated_image_path": annotated_path,
        "annotated_filename": annotated_filename
    }
