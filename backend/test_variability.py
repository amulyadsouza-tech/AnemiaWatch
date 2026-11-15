"""
AnemiaWatch – Variability & Error-Handling Test
Confirms predictions vary across distinct images and errors handled correctly.
"""
import os, sys, io
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)
WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ── Authenticate ─────────────────────────────────────────────────────────────
EMAIL, PASSWORD = "balkis@example.com", "Password123!"
r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
token = r.json().get("access_token", "")
headers = {"Authorization": f"Bearer {token}"}

results_hb = []

def nail_post(filepath, label):
    with open(filepath, "rb") as f:
        resp = client.post("/api/screening/nail",
                           files={"file": (os.path.basename(filepath), f, "image/jpeg")},
                           headers=headers)
    d = resp.json()
    hb = d.get("estimated_hb")
    results_hb.append(hb)
    print(f"{label}")
    print(f"  Status    : {resp.status_code}")
    print(f"  Hb        : {hb} g/dL")
    print(f"  Category  : {d.get('classification', {}).get('category')}")
    print(f"  Nails     : {d.get('nail_count')}")
    print(f"  Confidence: {d.get('confidence')}%")
    print(f"  Quality   : {d.get('quality', {}).get('status')}\n")
    return hb

print("=" * 60)
print("TEST RUN 2 — VARIABILITY TESTS")
print("=" * 60 + "\n")

nail_path_1 = os.path.join(WORKSPACE, "image and vedio reference on uiux", "images.jpg")
nail_path_2 = os.path.join(WORKSPACE, "image and vedio reference on uiux", "images (1).jpg")
eye_path = os.path.join(WORKSPACE, "hemoglobin-deficiency-detection", "Repository", "palpebral.jpg")

hb_a = nail_post(nail_path_1, "TEST A — Hand Image 1 (images.jpg) → /api/screening/nail")
hb_b = nail_post(nail_path_2, "TEST B — Hand Image 2 (images (1).jpg) → /api/screening/nail")

# ── TEST C: conjunctiva endpoint ─────────────────────────────────────────────
print("TEST C — Palpebral Conjunctiva Image (palpebral.jpg) → /api/screening/conjunctiva")
with open(eye_path, "rb") as f:
    resp = client.post("/api/screening/conjunctiva",
                       files={"file": ("palpebral.jpg", f, "image/jpeg")},
                       headers=headers)
d = resp.json()
hb_c = d.get("estimated_hb")
results_hb.append(hb_c)
print(f"  Status    : {resp.status_code}")
print(f"  Hb        : {hb_c} g/dL")
print(f"  EI        : {d.get('erythema_index'):.2f}")
print(f"  Category  : {d.get('classification', {}).get('category')}")
print(f"  Confidence: {d.get('confidence')}%\n")

# ── TEST D: invalid file type → expect 400 ───────────────────────────────────
print("TEST D — Text file → /api/screening/nail (expect 400)")
resp_bad = client.post("/api/screening/nail",
                       files={"file": ("bad.txt", io.BytesIO(b"not an image"), "text/plain")},
                       headers=headers)
print(f"  Status: {resp_bad.status_code}  {'PASS ✓' if resp_bad.status_code == 400 else 'FAIL ✗'}")
print(f"  Detail: {resp_bad.text[:100]}\n")

# ── SUMMARY ───────────────────────────────────────────────────────────────────
valid_hbs = [v for v in results_hb if v is not None]
different = len(set(valid_hbs)) == len(valid_hbs)
no_fixed = all(5.0 < v < 18.0 for v in valid_hbs)
invalid_ok = resp_bad.status_code == 400

print("=" * 60)
print("VARIABILITY & ERROR SUMMARY")
print(f"  Test A (Hand 1 → nail):      {hb_a} g/dL")
print(f"  Test B (Hand 2 → nail):      {hb_b} g/dL")
print(f"  Test C (Eye → conjunctiva):  {hb_c} g/dL")
print(f"  Test D (invalid file):       {'PASS ✓' if invalid_ok else 'FAIL ✗'} (HTTP {resp_bad.status_code})")
print(f"\n  All predictions distinct:    {'PASS ✓' if different else 'FAIL ✗'}")
print(f"  All values in realistic range: {'PASS ✓' if no_fixed else 'FAIL ✗'}")

all_pass = different and no_fixed and invalid_ok
print(f"\n{'ALL VARIABILITY TESTS PASSED ✓' if all_pass else 'SOME TESTS NEED REVIEW ⚠'}")
if not all_pass:
    sys.exit(1)
