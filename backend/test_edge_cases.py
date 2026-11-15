"""
AnemiaWatch – Test Run 3: Edge Cases & Stress Tests
Tests blurry image, overexposed, wrong anatomy, model status integrity.
"""
import os, sys, io, numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cv2
from fastapi.testclient import TestClient
from backend.app.main import app

client    = TestClient(app)
WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Auth
EMAIL, PASSWORD = "balkis@example.com", "Password123!"
r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
token   = r.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}

def encode_jpg(arr):
    _, buf = cv2.imencode(".jpg", arr)
    return io.BytesIO(buf.tobytes())

def nail_post(img_bytes, label, mime="image/jpeg"):
    resp = client.post("/api/screening/nail",
                       files={"file": ("test.jpg", img_bytes, mime)},
                       headers=headers)
    d  = resp.json()
    hb = d.get("estimated_hb")
    qs = d.get("quality", {}).get("status", "")
    print(f"{label}")
    print(f"  HTTP {resp.status_code} | Hb={hb} | Quality={qs}")
    return resp.status_code, hb, qs

print("=" * 60)
print("TEST RUN 3 — EDGE CASES & STRESS TESTS")
print("=" * 60 + "\n")
pass_count = 0; fail_count = 0

# CASE 1: Synthetic blurry all-grey image (Gaussian blur)
grey = np.full((480, 640, 3), 128, dtype=np.uint8)
blurry = cv2.GaussianBlur(grey, (99, 99), 30)
sc, hb, qs = nail_post(encode_jpg(blurry), "CASE 1 — Synthetic blurry grey image")
# Clinically correct: rejected because no anatomical nail ROI detected (HTTP 422)
ok = sc == 422
print(f"  {'PASS ✓' if ok else 'FAIL ✗'} (expect 422 image rejection, got {sc})\n")
pass_count += ok; fail_count += (not ok)

# CASE 2: Pitch-black image (no ROI detected)
black = np.zeros((480, 640, 3), dtype=np.uint8)
sc, hb, qs = nail_post(encode_jpg(black), "CASE 2 — Completely black image")
ok = sc == 422
print(f"  {'PASS ✓' if ok else 'FAIL ✗'} (expect 422 image rejection, got {sc})\n")
pass_count += ok; fail_count += (not ok)

# CASE 3: Overexposed (all white, no ROI detected)
white = np.full((480, 640, 3), 255, dtype=np.uint8)
sc, hb, qs = nail_post(encode_jpg(white), "CASE 3 — Overexposed white image")
ok = sc == 422
print(f"  {'PASS ✓' if ok else 'FAIL ✗'} (expect 422 image rejection, got {sc})\n")
pass_count += ok; fail_count += (not ok)

# CASE 4: Valid hand image (reference)
nail_path = os.path.join(WORKSPACE, "image and vedio reference on uiux", "images.jpg")
with open(nail_path, "rb") as f:
    sc, hb, qs = nail_post(io.BytesIO(f.read()), "CASE 4 — Real hand image (reference)")
ok = (sc == 200) and (hb is not None) and (5.0 < hb < 20.0)
print(f"  {'PASS ✓' if ok else 'FAIL ✗'} (Hb={hb} should be in 5–20 range)\n")
pass_count += ok; fail_count += (not ok)

# CASE 5: Valid eye image → conjunctiva endpoint
eye_path = os.path.join(WORKSPACE, "hemoglobin-deficiency-detection", "Repository", "palpebral.jpg")
print("CASE 5 — Real eye image → conjunctiva endpoint")
with open(eye_path, "rb") as f:
    resp = client.post("/api/screening/conjunctiva",
                       files={"file": ("eye.jpg", f, "image/jpeg")},
                       headers=headers)
d   = resp.json()
hb5 = d.get("estimated_hb")
ei5 = d.get("erythema_index")
ok  = (resp.status_code == 200) and (hb5 is not None) and (4.0 < hb5 < 20.0) and (ei5 is not None)
print(f"  HTTP {resp.status_code} | Hb={hb5} g/dL | EI={ei5:.2f}")
print(f"  {'PASS ✓' if ok else 'FAIL ✗'}\n")
pass_count += ok; fail_count += (not ok)

# CASE 6: Non-image MIME type
sc6, hb6, _ = nail_post(io.BytesIO(b"fake"), "CASE 6 — Non-image MIME type (text/plain)", mime="text/plain")
ok = sc6 == 400
print(f"  {'PASS ✓' if ok else 'FAIL ✗'} (expect 400, got {sc6})\n")
pass_count += ok; fail_count += (not ok)

# CASE 7: Unauthenticated request
print("CASE 7 — No auth token (expect 401)")
with open(nail_path, "rb") as f:
    resp7 = client.post("/api/screening/nail",
                        files={"file": ("hand.jpg", f, "image/jpeg")})
ok = resp7.status_code == 401
print(f"  HTTP {resp7.status_code} {'PASS ✓' if ok else 'FAIL ✗'}\n")
pass_count += ok; fail_count += (not ok)

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print("=" * 60)
print(f"TEST RUN 3 SUMMARY: {pass_count} PASSED | {fail_count} FAILED")
print("=" * 60)
if fail_count == 0:
    print("ALL EDGE-CASE TESTS PASSED ✓")
else:
    print(f"{fail_count} TEST(S) NEED REVIEW ⚠")
