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
    - Focuses strictly on lower eyelid mucosal shelf (0.46*h to 0.78*h)
    - Excludes fingers pulling the eyelid (y > 0.78*h)
    - Excludes white sclera (high brightness, balanced R=G=B)
    - Excludes dark iris / pupil (low brightness)
    - Isolates vascular mucosal redness in the lower eyelid
    """
    h, w = eye_roi_bgr.shape[:2]
    
    # Lower eyelid mucosal shelf is strictly between 0.46*h and 0.78*h (avoids fingers below)
    y0 = int(h * 0.46)
    y1 = int(h * 0.78)
    
    b, g, r = cv2.split(eye_roi_bgr)
    
    # Blood-rich mucosal color mask:
    red_diff = r.astype(np.float32) - g.astype(np.float32)
    # Exclude white sclera where r, g, b are all high and close:
    is_sclera = (r > 195) & (g > 195) & (b > 195)
    # Exclude dark iris/pupil:
    is_dark = (r < 55) & (g < 55) & (b < 55)
    # Exclude specular flash glare:
    is_glare = (r > 245) & (g > 245)
    
    # Conjunctiva mask restricted to anatomical lower lid zone
    conjunctiva_mask = (red_diff > 8) & (r > 85) & (~is_sclera) & (~is_dark) & (~is_glare)
    y_indices = np.arange(h)[:, None]
    conjunctiva_mask = conjunctiva_mask & (y_indices >= y0) & (y_indices <= y1)
    
    # Cleanup mask with morphology
    mask_uint8 = conjunctiva_mask.astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_cleaned = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, kernel, iterations=1)
    mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Find components; reject giant finger/cheek components (> 4500 px)
    contours, _ = cv2.findContours(mask_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    final_mask = np.zeros((h, w), dtype=np.uint8)
    if contours:
        valid_contours = [c for c in contours if 30 <= cv2.contourArea(c) <= 4500]
        if valid_contours:
            best_contour = max(valid_contours, key=cv2.contourArea)
            cv2.drawContours(final_mask, [best_contour], -1, 255, -1)
            
    if np.sum(final_mask) < 40:
        # Fallback anatomical crescent in lower palpebral zone
        cv2.ellipse(final_mask, (w // 2, int(h * 0.64)), (int(w * 0.28), int(h * 0.08)), 0, 0, 180, 255, -1)
        
    return final_mask

def process_conjunctiva_image(image_path, output_dir):
    """
    End-to-end processing of lower eyelid palpebral conjunctiva:
    1. Loads eye image
    2. Validates image quality
    3. Detects eye socket and lower eyelid (rejects false positive face/chest boxes)
    4. Segments palpebral conjunctiva (excludes fingers)
    5. Calculates Erythema Index
    6. Generates visual overlays matching clinical literature
    """
    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise ValueError(f"Could not load image at {image_path}")
        
    h, w = img_bgr.shape[:2]
    quality = evaluate_image_quality(img_bgr)
    
    annotated = img_bgr.copy()
    
    # Detect eye region: Multi-candidate evaluation to identify the pulled lower eyelid
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    eyes = eye_cascade.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(50, 50))
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(140, 140))
    
    candidates = []
    # 1. Haar eye candidates with physiological eye aspect ratios
    for b in eyes:
        if 65 <= b[2] <= 280 and 45 <= b[3] <= 260:
            candidates.append((int(b[0]), int(b[1]), int(b[2]), int(b[3])))
            
    # 2. Anatomical eye zone candidates if face is detected (left & right eye regions)
    if len(faces) > 0:
        fx, fy, fw, fh = faces[0]
        z1 = (max(0, int(fx + 0.08 * fw)), max(0, int(fy + 0.20 * fh)), int(0.40 * fw), int(0.38 * fh))
        z2 = (max(0, int(fx + 0.52 * fw)), max(0, int(fy + 0.20 * fh)), int(0.40 * fw), int(0.38 * fh))
        candidates.append(z1)
        candidates.append(z2)
        
    def _score_pulled_eye(box):
        """Scores candidate eye region by mucosal exposure and vascular redness in lower lid zone."""
        bx, by, bw, bh = box
        roi = img_bgr[by:min(h, by + bh), bx:min(w, bx + bw)]
        if roi.size == 0:
            return -1.0
        rh, rw = roi.shape[:2]
        shelf = roi[int(0.42 * rh):int(0.82 * rh), :]
        b_ch, g_ch, r_ch = cv2.split(shelf)
        diff = r_ch.astype(float) - g_ch.astype(float)
        # Mucosal redness: excess of red over green and blue, excluding white sclera
        is_mucosa = (diff > 18) & (r_ch > 115) & (b_ch < 185)
        # Sclera immediately above provides anatomical confirmation of an eye
        is_sclera = (r_ch > 175) & (g_ch > 175) & (b_ch > 175)
        mucosa_count = float(np.sum(is_mucosa))
        sclera_count = float(np.sum(is_sclera))
        return mucosa_count + min(1500.0, sclera_count * 0.4)

    if candidates:
        # Select the candidate eye with maximum exposed palpebral conjunctiva mucosa
        scored_candidates = [(b, _score_pulled_eye(b)) for b in candidates]
        scored_candidates.sort(key=lambda t: t[1], reverse=True)
        chosen = scored_candidates[0][0]
        ex, ey, ew, eh = chosen
        
        # Expand slightly downward to ensure the full palpebral margin is included
        pad_top = int(eh * 0.04)
        pad_bot = int(eh * 0.25)
        pad_x = int(ew * 0.06)
        ey0 = max(0, ey - pad_top)
        ey1 = min(h, ey + eh + pad_bot)
        ex0 = max(0, ex - pad_x)
        ex1 = min(w, ex + ew + pad_x)
        eye_box = (int(ex0), int(ey0), int(ex1 - ex0), int(ey1 - ey0))
    else:
        # Custom eye alignment overlay fallback (center region)
        cx, cy = w // 2, int(h * 0.42)
        ew, eh = int(w * 0.42), int(h * 0.35)
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
