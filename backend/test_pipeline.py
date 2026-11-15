import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_full_pipeline():
    print("Testing /api/health...")
    res = client.get("/api/health")
    assert res.status_code == 200, res.text
    print("Health response:", res.json())
    
    # 1. Register test patient
    print("\nTesting Registration...")
    reg_data = {
        "email": "balkis@example.com",
        "password": "Password123!",
        "full_name": "Balkis Arifatul",
        "role": "patient",
        "age": 24,
        "sex": "female",
        "is_pregnant": False,
        "blood_type": "O+"
    }
    res = client.post("/api/auth/register", json=reg_data)
    if res.status_code == 400 and "already registered" in res.text:
        # login instead
        login_res = client.post("/api/auth/login", json={"email": "balkis@example.com", "password": "Password123!"})
        token = login_res.json()["access_token"]
    else:
        assert res.status_code == 200, res.text
        token = res.json()["access_token"]
        
    headers = {"Authorization": f"Bearer {token}"}
    print("Patient authenticated successfully. Token received.")
    
    # 2. Test Conjunctiva screening using existing palpebral.jpg
    conj_img_path = os.path.abspath("hemoglobin-deficiency-detection/Repository/palpebral.jpg")
    print(f"\nTesting Conjunctiva Screening with {conj_img_path}...")
    with open(conj_img_path, "rb") as f:
        res = client.post(
            "/api/screening/conjunctiva",
            files={"file": ("palpebral.jpg", f, "image/jpeg")},
            headers=headers
        )
    assert res.status_code == 200, res.text
    conj_res = res.json()
    print("Conjunctiva Screening Output:")
    print(f" - Estimated Hb: {conj_res['estimated_hb']} {conj_res['unit']}")
    print(f" - Category: {conj_res['classification']['category']}")
    print(f" - AI Confidence: {conj_res['confidence']}%")
    print(f" - Erythema Index: {conj_res['erythema_index']}")
    print(f" - Validation: {conj_res['validation_status']}")
    
    # 3. Test Nail bed screening using existing images.jpg
    nail_img_path = os.path.abspath("image and vedio reference on uiux/images.jpg")
    print(f"\nTesting Nail Bed Screening with {nail_img_path}...")
    with open(nail_img_path, "rb") as f:
        res = client.post(
            "/api/screening/nail",
            files={"file": ("fingernails.jpg", f, "image/jpeg")},
            headers=headers
        )
    assert res.status_code == 200, res.text
    nail_res = res.json()
    print("Nail Bed Screening Output:")
    print(f" - Estimated Hb: {nail_res['estimated_hb']} {nail_res['unit']}")
    print(f" - Category: {nail_res['classification']['category']}")
    print(f" - Confidence: {nail_res['confidence']}%")
    print(f" - Detected Nails: {nail_res['nail_count']}")
    
    # 4. Test History
    print("\nTesting History...")
    res = client.get("/api/screening/history", headers=headers)
    assert res.status_code == 200
    screenings = res.json()["screenings"]
    print(f"Found {len(screenings)} historical records for patient.")
    
    # 5. Test PDF download for conjunctiva
    screening_id = conj_res["screening_id"]
    print(f"\nTesting PDF Report download for screening #{screening_id}...")
    pdf_res = client.get(f"/api/screening/{screening_id}/pdf", headers=headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    print(f"PDF successfully retrieved ({len(pdf_res.content)} bytes).")
    
    # 6. Test Doctor Registration & Dashboard
    print("\nTesting Doctor Dashboard...")
    doc_data = {
        "email": "dr.smith@hospital.org",
        "password": "DoctorPass123!",
        "full_name": "Dr. Sarah Smith, MD",
        "role": "doctor"
    }
    client.post("/api/auth/register", json=doc_data)
    doc_login = client.post("/api/auth/login", json={"email": "dr.smith@hospital.org", "password": "DoctorPass123!"})
    doc_token = doc_login.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}
    
    dash_res = client.get("/api/doctor/dashboard", headers=doc_headers)
    assert dash_res.status_code == 200, dash_res.text
    print("Doctor Dashboard Metrics:", dash_res.json()["metrics"])
    
    pat_res = client.get("/api/doctor/patients", headers=doc_headers)
    assert pat_res.status_code == 200
    print(f"Doctor Patients list count: {len(pat_res.json()['patients'])}")
    
    print("\nALL BACKEND TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_full_pipeline()
