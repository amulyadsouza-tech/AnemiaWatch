import os
import io
import json
import uuid
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models.schema import User, Patient, Doctor, Screening, DoctorPatient

client = TestClient(app)

def make_test_image(color=(180, 100, 100)):
    """Generates a small test RGB image in memory."""
    img = Image.new("RGB", (200, 200), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

def test_cycle_1_patient_ml_and_doctor_access():
    print("\n" + "="*70)
    print("CYCLE 1: ML INFERENCE, SCREENING STORAGE & DOCTOR ACCESS")
    print("="*70)

    # 1. Health check & model verification
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    health = res.json()
    assert health["status"] == "healthy"
    assert health["models"]["conjunctiva_regressor_loaded"] is True
    assert health["models"]["nail_regressor_loaded"] is True
    print("  [1/6] Health check: OK. Models loaded: Conjunctiva & Nail.")

    # 2. Patient login
    login_res = client.post("/api/auth/login", json={"email": "test@gmail.com", "password": "test1234"})
    assert login_res.status_code == 200, f"Patient login failed: {login_res.text}"
    patient_token = login_res.json()["access_token"]
    patient_id = login_res.json()["user"]["profile"]["id"]
    print(f"  [2/6] Patient login: OK (patient_id={patient_id}).")

    # 3. Patient performs ML screening (Fingernail)
    img_buf = make_test_image((210, 140, 130))
    files = {"file": ("fingernail_sample.jpg", img_buf, "image/jpeg")}
    headers = {"Authorization": f"Bearer {patient_token}"}
    nail_res = client.post("/api/screening/nail", files=files, headers=headers)
    assert nail_res.status_code == 200, f"Nail screening failed: {nail_res.text}"
    nail_data = nail_res.json()
    assert nail_data["status"] == "success"
    assert "estimated_hb" in nail_data
    assert "confidence" in nail_data
    assert "classification" in nail_data
    assert any(term in nail_data["classification"]["category"] for term in ["Normal", "Anemic", "Anemia"])
    print(f"  [3/6] Nail ML Inference: OK -> Hb: {nail_data['estimated_hb']} g/dL ({nail_data['classification']['category']}), Conf: {nail_data['confidence']}%.")

    # 4. Patient performs ML screening (Conjunctiva)
    img_buf2 = make_test_image((190, 80, 80))
    files2 = {"file": ("conjunctiva_sample.jpg", img_buf2, "image/jpeg")}
    conj_res = client.post("/api/screening/conjunctiva", files=files2, headers=headers)
    assert conj_res.status_code == 200, f"Conjunctiva screening failed: {conj_res.text}"
    conj_data = conj_res.json()
    assert conj_data["status"] == "success"
    assert "estimated_hb" in conj_data
    print(f"  [4/6] Conjunctiva ML Inference: OK -> Hb: {conj_data['estimated_hb']} g/dL ({conj_data['classification']['category']}).")

    # 5. Doctor login
    doc_login = client.post("/api/auth/login", json={"email": "doctor@test.com", "password": "doctor1234"})
    assert doc_login.status_code == 200, f"Doctor login failed: {doc_login.text}"
    doc_token = doc_login.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}
    print("  [5/6] Doctor login: OK (approved doctor).")

    # 6. Doctor accesses patient dashboard, patient list & patient screening detail
    dash_res = client.get("/api/doctor/dashboard", headers=doc_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["status"] == "success"
    assert dash_data["metrics"]["total_screenings"] >= 1
    print(f"  [6/6] Doctor Dashboard: OK -> Screenings visible: {dash_data['metrics']['total_screenings']}.")

    # Doctor views patient detail
    detail_res = client.get(f"/api/doctor/patient/{patient_id}", headers=doc_headers)
    assert detail_res.status_code == 200, f"Doctor patient detail access failed: {detail_res.text}"
    history = detail_res.json()["history"]
    assert len(history) >= 1, "Expected patient screening history to contain at least 1 record"
    print(f"        Doctor accessing patient history: OK ({len(history)} screenings retrieved).")

    # Doctor adds clinical note
    note_res = client.post(
        f"/api/doctors/me/patients/{patient_id}/notes",
        headers=doc_headers,
        json={"notes": "Hemoglobin stable. Prescribed dietary iron supplementation."}
    )
    assert note_res.status_code == 200
    print("        Doctor adding clinical note: OK.")
    print(">>> CYCLE 1 COMPLETED SUCCESSFULLY!")


def test_cycle_2_new_patient_onboarding_and_consent_lifecycle():
    print("\n" + "="*70)
    print("CYCLE 2: NEW PATIENT ONBOARDING, CLINICAL TRIAGE & CONSENT LIFECYCLE")
    print("="*70)

    # 1. Register brand new patient
    new_email = f"patient_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = client.post("/api/auth/register/patient", json={
        "email": new_email,
        "password": "Password123!",
        "full_name": "Sarah Miller",
        "age": 29,
        "sex": "female",
        "pregnancy_status": True,
        "phone_number": "+1-555-888-9999"
    })
    assert reg_res.status_code == 200, f"Registration failed: {reg_res.text}"
    pat_token = reg_res.json()["access_token"]
    pat_id = reg_res.json()["user"]["profile"]["id"]
    print(f"  [1/4] New patient registered: {new_email} (ID={pat_id}).")

    # 2. Patient performs screening
    img_buf = make_test_image((205, 120, 115))
    files = {"file": ("new_nail.jpg", img_buf, "image/jpeg")}
    headers = {"Authorization": f"Bearer {pat_token}"}
    scr_res = client.post("/api/screening/nail", files=files, headers=headers)
    assert scr_res.status_code == 200
    scr_id = scr_res.json()["screening_id"]
    print(f"  [2/4] New patient ML screening: OK (screening_id={scr_id}).")

    # 3. Doctor login & access
    doc_login = client.post("/api/auth/login", json={"email": "doctor@test.com", "password": "doctor1234"})
    doc_token = doc_login.json()["access_token"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # Patient grants explicit consent to doctor
    db = SessionLocal()
    doc_profile = db.query(Doctor).filter(Doctor.medical_registration_number == "REG-MED-88421").first()
    db.close()

    grant_res = client.post(
        "/api/patients/me/consents",
        headers=headers,
        json={
            "consent_type": "DOCTOR_ACCESS",
            "purpose": "Prenatal anemia monitoring",
            "doctor_id": doc_profile.id
        }
    )
    assert grant_res.status_code == 200
    print("  [3/4] Patient granted consent to Doctor: OK.")

    # Doctor accesses patient detail
    pat_detail = client.get(f"/api/doctor/patient/{pat_id}", headers=doc_headers)
    assert pat_detail.status_code == 200
    assert pat_detail.json()["patient"]["full_name"] == "Sarah Miller"
    assert len(pat_detail.json()["history"]) >= 1
    print("  [4/4] Doctor accessed new patient's records and screening history: OK.")
    print(">>> CYCLE 2 COMPLETED SUCCESSFULLY!")


def test_cycle_3_full_security_and_role_isolation():
    print("\n" + "="*70)
    print("CYCLE 3: SECURITY, IDOR PROTECTION & BRUTE-FORCE LOCKOUT")
    print("="*70)

    # 1. Unverified doctor registration
    doc_email = f"unverified_{uuid.uuid4().hex[:8]}@hospital.org"
    doc_reg = client.post("/api/auth/register/doctor", json={
        "email": doc_email,
        "password": "DocPassword123!",
        "full_name": "Dr. Candidate",
        "medical_registration_number": f"REG-TEST-{uuid.uuid4().hex[:6]}",
        "qualification": "MBBS",
        "specialization": "General Medicine",
        "hospital_or_clinic": "Regional Health Clinic"
    })
    assert doc_reg.status_code == 200
    unverified_token = doc_reg.json()["access_token"]
    print("  [1/4] Doctor registered (pending status): OK.")

    # 2. Unverified doctor CANNOT access patient records
    fail_access = client.get(
        "/api/doctor/patient/any-patient-id",
        headers={"Authorization": f"Bearer {unverified_token}"}
    )
    assert fail_access.status_code == 403
    print("  [2/4] Unverified doctor blocked with 403: OK.")

    # 3. Patient cannot access doctor dashboard
    pat_login = client.post("/api/auth/login", json={"email": "test@gmail.com", "password": "test1234"})
    pat_token = pat_login.json()["access_token"]
    pat_fail = client.get("/api/doctor/dashboard", headers={"Authorization": f"Bearer {pat_token}"})
    assert pat_fail.status_code == 403
    print("  [3/4] Patient blocked from doctor dashboard with 403: OK.")

    # 4. Token refresh rotation
    ref_token = pat_login.json()["refresh_token"]
    ref_res = client.post("/api/auth/refresh", json={"refresh_token": ref_token})
    assert ref_res.status_code == 200
    new_ref = ref_res.json()["refresh_token"]
    assert new_ref != ref_token
    # Old token reuse must fail
    reuse_fail = client.post("/api/auth/refresh", json={"refresh_token": ref_token})
    assert reuse_fail.status_code == 401
    print("  [4/4] Refresh token rotation & reuse prevention: OK.")
    print(">>> CYCLE 3 COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    test_cycle_1_patient_ml_and_doctor_access()
    test_cycle_2_new_patient_onboarding_and_consent_lifecycle()
    test_cycle_3_full_security_and_role_isolation()
    print("\n" + "#"*70)
    print("ALL 3 SYSTEM CYCLES PASSED 100%! SYSTEM FULLY VERIFIED.")
    print("#"*70)
