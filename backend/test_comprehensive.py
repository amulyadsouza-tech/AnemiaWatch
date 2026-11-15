"""
AnemiaWatch — Comprehensive End-to-End Test Suite (HF26-35)
Validates all features: Auth, Profiles, Nail Screening, Conjunctiva Screening,
PDF Reports, History, Doctor Portal, and Error Handling.
"""
import sys
import os
import io
import time
import requests

BASE = "http://127.0.0.1:8000"
WORKSPACE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

passed = 0
failed = 0

def check(name, condition, extra=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {name} {extra}")
        passed += 1
    else:
        print(f"  [FAIL] {name} {extra}")
        failed += 1

print("=" * 70)
print("ANEMIAWATCH COMPREHENSIVE END-TO-END VERIFICATION")
print("=" * 70)

# ── 1. Backend Health & ML Models Status ─────────────────────────────────────
print("\n--- 1. Health & Model Architecture ---")
r = requests.get(f"{BASE}/api/health")
check("Health endpoint returns 200", r.status_code == 200)
health = r.json()
check("Database connected", health.get("database") == "sqlite_connected")
models = health.get("models", {})
check("Conjunctiva regressor loaded", models.get("conjunctiva_regressor_loaded") is True)
check("Conjunctiva classifier loaded", models.get("conjunctiva_classifier_loaded") is True)
check("Nail regressor loaded", models.get("nail_regressor_loaded") is True)

# ── 2. Authentication: Registration & Validation ─────────────────────────────
print("\n--- 2. Authentication & User Profile ---")
timestamp = int(time.time())
test_email = f"patient_{timestamp}@health.org"
test_pass = "SecurePass123!"

# 2a. Register new user
reg_payload = {
    "email": test_email,
    "password": test_pass,
    "full_name": f"Test Patient {timestamp}",
    "role": "patient",
    "age": 26,
    "sex": "female",
    "is_pregnant": False,
    "blood_type": "A+"
}
r = requests.post(f"{BASE}/api/auth/register", json=reg_payload)
check("Register returns 200", r.status_code == 200)
reg_data = r.json()
token = reg_data.get("access_token")
check("Registration returns JWT token", bool(token))
check("User profile populated", reg_data.get("user", {}).get("profile", {}).get("age") == 26)

# 2b. Prevent duplicate registration
r_dup = requests.post(f"{BASE}/api/auth/register", json=reg_payload)
check("Duplicate email rejected (HTTP 400)", r_dup.status_code == 400)
check("Meaningful duplicate error message", "already registered" in r_dup.text.lower())

# 2c. Login verification
r_login = requests.post(f"{BASE}/api/auth/login", json={"email": test_email, "password": test_pass})
check("Login with correct credentials returns 200", r_login.status_code == 200)

# 2d. Reject wrong credentials
r_bad_login = requests.post(f"{BASE}/api/auth/login", json={"email": test_email, "password": "WrongPassword"})
check("Login with wrong password rejected (HTTP 401)", r_bad_login.status_code == 401)

# 2e. Get Me & Update Profile
headers = {"Authorization": f"Bearer {token}"}
r_me = requests.get(f"{BASE}/api/auth/me", headers=headers)
check("Get profile (/api/auth/me) returns 200", r_me.status_code == 200)

r_upd = requests.put(f"{BASE}/api/auth/profile", json={"age": 27, "is_pregnant": True}, headers=headers)
check("Update profile returns 200", r_upd.status_code == 200)
check("Profile update reflected", r_upd.json().get("profile", {}).get("age") == 27)

# ── 3. Nail-Bed Screening Pipeline ───────────────────────────────────────────
print("\n--- 3. Nail-Bed ML Screening ---")
nail_img_path = os.path.join(WORKSPACE, "image and vedio reference on uiux", "images.jpg")
with open(nail_img_path, "rb") as f:
    r_nail = requests.post(f"{BASE}/api/screening/nail",
                           files={"file": ("hand_test.jpg", f, "image/jpeg")},
                           headers=headers)
check("Nail screening returns 200", r_nail.status_code == 200)
nail_res = r_nail.json()
nail_screening_id = nail_res.get("screening_id")
hb_nail = nail_res.get("estimated_hb")
check("Estimated Hb present and within physiological range", 5.0 <= hb_nail <= 20.0, f"({hb_nail} g/dL)")
check("Screening category assigned", bool(nail_res.get("classification", {}).get("category")))
check("Fingernails detected by computer vision", nail_res.get("nail_count", 0) > 0, f"({nail_res.get('nail_count')} ROIs)")
check("Processed image URL returned", bool(nail_res.get("processed_image_url")))

# Verify image is accessible
r_img = requests.get(f"{BASE}{nail_res.get('processed_image_url')}")
check("Processed inspection image served via HTTP", r_img.status_code == 200 and len(r_img.content) > 1000)

# ── 4. Lower-Eyelid / Conjunctiva Screening Pipeline ─────────────────────────
print("\n--- 4. Lower-Eyelid Palpebral Conjunctiva Screening ---")
eye_img_path = os.path.join(WORKSPACE, "hemoglobin-deficiency-detection", "Repository", "palpebral.jpg")
with open(eye_img_path, "rb") as f:
    r_eye = requests.post(f"{BASE}/api/screening/conjunctiva",
                          files={"file": ("palpebral_test.jpg", f, "image/jpeg")},
                          headers=headers)
check("Conjunctiva screening returns 200", r_eye.status_code == 200)
eye_res = r_eye.json()
eye_screening_id = eye_res.get("screening_id")
hb_eye = eye_res.get("estimated_hb")
ei_val = eye_res.get("erythema_index")
check("Erythema Index calculated", ei_val is not None and ei_val > 0, f"(EI={ei_val:.2f})")
check("Harvard dataset model prediction present", 4.5 <= hb_eye <= 19.0, f"({hb_eye} g/dL)")
check("Clinical recommendations present", bool(eye_res.get("recommendations", {}).get("prevention")))

# ── 5. PDF Clinical Report Generation & Retrieval ────────────────────────────
print("\n--- 5. PDF Clinical Reports ---")
# 5a. Retrieve with header
r_pdf_hdr = requests.get(f"{BASE}/api/screening/{nail_screening_id}/pdf", headers=headers)
check("PDF download with Auth Header returns 200", r_pdf_hdr.status_code == 200 and r_pdf_hdr.headers.get("content-type") == "application/pdf")

# 5b. Retrieve with query param (?token=...) for browser window.open
r_pdf_qry = requests.get(f"{BASE}/api/screening/{nail_screening_id}/pdf?token={token}")
check("PDF download with ?token query param returns 200", r_pdf_qry.status_code == 200 and len(r_pdf_qry.content) > 5000)

# ── 6. Screening History ─────────────────────────────────────────────────────
print("\n--- 6. Screening History & Articles ---")
r_hist = requests.get(f"{BASE}/api/screening/history", headers=headers)
check("History endpoint returns 200", r_hist.status_code == 200)
hist_records = r_hist.json().get("screenings", [])
check("History contains created screenings", len(hist_records) >= 2)

r_art = requests.get(f"{BASE}/api/screening/articles")
check("Educational articles returned", r_art.status_code == 200 and len(r_art.json()) >= 3)

# ── 7. Doctor Dashboard & Clinical Management ────────────────────────────────
print("\n--- 7. Doctor Portal & RBAC ---")
# 7a. Patient forbidden from doctor dashboard
r_doc_forbidden = requests.get(f"{BASE}/api/doctor/dashboard", headers=headers)
check("Patient rejected from doctor dashboard (HTTP 403)", r_doc_forbidden.status_code == 403)

# 7b. Register & login as doctor
doc_email = f"dr_{timestamp}@hospital.org"
doc_pass = "DoctorPass123!"
requests.post(f"{BASE}/api/auth/register", json={
    "email": doc_email, "password": doc_pass,
    "full_name": f"Dr. Alex Specialist {timestamp}",
    "role": "doctor"
})
doc_login = requests.post(f"{BASE}/api/auth/login", json={"email": doc_email, "password": doc_pass})
doc_token = doc_login.json().get("access_token")
doc_headers = {"Authorization": f"Bearer {doc_token}"}

# 7c. Access doctor dashboard
r_dash = requests.get(f"{BASE}/api/doctor/dashboard", headers=doc_headers)
check("Doctor dashboard returns 200", r_dash.status_code == 200)
check("Dashboard metrics computed", "total_screenings" in r_dash.json().get("metrics", {}))

# 7d. Doctor searches patients
r_pats = requests.get(f"{BASE}/api/doctor/patients?search=Test", headers=doc_headers)
check("Doctor patient search returns 200", r_pats.status_code == 200)

# ── 8. Error Handling & Edge Cases ───────────────────────────────────────────
print("\n--- 8. Error Handling & Validation ---")
# 8a. Invalid non-image file
r_bad_file = requests.post(f"{BASE}/api/screening/nail",
                           files={"file": ("document.txt", io.BytesIO(b"Hello world"), "text/plain")},
                           headers=headers)
check("Non-image file rejected (HTTP 400)", r_bad_file.status_code == 400)

# 8b. Missing authorization token
r_no_auth = requests.post(f"{BASE}/api/screening/nail",
                          files={"file": ("test.jpg", io.BytesIO(b"dummy"), "image/jpeg")})
check("Unauthenticated screening rejected (HTTP 401)", r_no_auth.status_code == 401)

# ── SUMMARY ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print(f"VERIFICATION SUMMARY: {passed} PASSED, {failed} FAILED")
print("=" * 70)
if failed == 0:
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    sys.exit(0)
else:
    print(f"{failed} test(s) failed.")
    sys.exit(1)
