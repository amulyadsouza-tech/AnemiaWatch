import os
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test database environment BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite:///./test_anemiawatch.db"
os.environ["JWT_SECRET"] = "test-secret-key-32-bytes-long-for-testing"
os.environ["ENVIRONMENT"] = "test"

from backend.app.database import Base, get_db
from backend.app.models.schema import User, Patient, Doctor, DoctorPatient, Screening, Consent, AuditLog
from backend.app.main import app

# Test database engine
TEST_DB_PATH = "./test_anemiawatch.db"
test_engine = create_engine("sqlite:///./test_anemiawatch.db", connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass

@pytest.fixture
def client():
    return TestClient(app)

# ─────────────────────────────────────────────────────────────────────────────
# 1. AUTHENTICATION TESTS
# ─────────────────────────────────────────────────────────────────────────────
def test_patient_registration_success(client):
    email = f"patient_{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Alice Patient",
        "age": 28,
        "sex": "female",
        "pregnancy_status": True
    }
    res = client.post("/auth/register/patient", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["role"] == "patient"
    assert data["user"]["profile"]["pregnancy_status"] is True

def test_patient_registration_duplicate_email(client):
    email = f"dup_{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "First User",
        "age": 24,
        "sex": "female"
    }
    res1 = client.post("/auth/register/patient", json=payload)
    assert res1.status_code == 200

    # Second registration with same email
    res2 = client.post("/auth/register/patient", json=payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"].lower()

def test_doctor_registration_pending_status(client):
    email = f"doc_{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "email": email,
        "password": "DocPassword123!",
        "full_name": "Dr. House",
        "medical_registration_number": f"REG-{uuid.uuid4().hex[:6]}",
        "qualification": "MD, Internal Medicine",
        "specialization": "Hematology",
        "hospital_or_clinic": "Princeton-Plainsboro",
        "experience": "12 years",
        "phone_number": "+1-555-0199"
    }
    res = client.post("/auth/register/doctor", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["role"] == "doctor"
    assert data["user"]["doctor_info"]["verification_status"] == "pending"

def test_login_successful(client):
    email = f"login_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/auth/register/patient", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Login Tester",
        "age": 25,
        "sex": "male"
    })

    res = client.post("/auth/login", json={
        "email": email,
        "password": "Password123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == email

def test_login_invalid_password(client):
    email = f"wrongpw_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/auth/register/patient", json={
        "email": email,
        "password": "CorrectPassword123!",
        "full_name": "Wrong Pass Tester"
    })

    res = client.post("/auth/login", json={
        "email": email,
        "password": "WrongPassword999!"
    })
    assert res.status_code == 401
    assert "invalid email or password" in res.json()["detail"].lower()

def test_login_lockout_after_max_attempts(client):
    email = f"lockout_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/auth/register/patient", json={
        "email": email,
        "password": "ValidPassword123!",
        "full_name": "Lockout Tester"
    })

    # Trigger 5 failed attempts
    for _ in range(5):
        client.post("/auth/login", json={"email": email, "password": "WrongPassword!"})

    # 6th attempt should be locked out with 403
    res = client.post("/auth/login", json={"email": email, "password": "ValidPassword123!"})
    assert res.status_code == 403
    assert "locked" in res.json()["detail"].lower()

def test_refresh_token_rotation(client):
    email = f"refresh_{uuid.uuid4().hex[:6]}@example.com"
    reg = client.post("/auth/register/patient", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Token Refresher"
    })
    tokens = reg.json()
    old_refresh = tokens["refresh_token"]

    # 1. Use refresh token
    ref_res = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert ref_res.status_code == 200
    new_data = ref_res.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    new_refresh = new_data["refresh_token"]
    assert new_refresh != old_refresh

    # 2. Reusing old refresh token must be rejected (Token reuse detection)
    reuse_res = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_res.status_code == 401
    assert "revoked" in reuse_res.json()["detail"].lower()

def test_logout_session_revocation(client):
    email = f"logout_{uuid.uuid4().hex[:6]}@example.com"
    reg = client.post("/auth/register/patient", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Logout Tester"
    })
    tokens = reg.json()
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    # Logout
    out_res = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {access}"},
        json={"refresh_token": refresh}
    )
    assert out_res.status_code == 200

    # Attempt to refresh with revoked token should fail
    fail_res = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert fail_res.status_code == 401

# ─────────────────────────────────────────────────────────────────────────────
# 2. AUTHORIZATION & RBAC TESTS
# ─────────────────────────────────────────────────────────────────────────────
def test_patient_self_access_only(client):
    # Patient 1
    p1 = client.post("/auth/register/patient", json={
        "email": f"p1_{uuid.uuid4().hex[:6]}@example.com",
        "password": "Password123!",
        "full_name": "Patient One"
    }).json()

    # Patient 2
    p2 = client.post("/auth/register/patient", json={
        "email": f"p2_{uuid.uuid4().hex[:6]}@example.com",
        "password": "Password123!",
        "full_name": "Patient Two"
    }).json()

    # P1 gets own profile
    res1 = client.get("/patients/me", headers={"Authorization": f"Bearer {p1['access_token']}"})
    assert res1.status_code == 200
    assert res1.json()["full_name"] == "Patient One"

    # P1 cannot view doctor portal (doctorOnly)
    doc_portal_res = client.get("/doctors/me", headers={"Authorization": f"Bearer {p1['access_token']}"})
    assert doc_portal_res.status_code == 403

def test_unverified_doctor_blocked_from_patient_records(client):
    # Unverified doctor
    doc_res = client.post("/auth/register/doctor", json={
        "email": f"unverified_{uuid.uuid4().hex[:6]}@example.com",
        "password": "DocPassword123!",
        "full_name": "Dr. Unverified",
        "medical_registration_number": f"REG-{uuid.uuid4().hex[:6]}",
        "qualification": "MBBS",
        "specialization": "Pediatrics",
        "hospital_or_clinic": "General Clinic"
    }).json()
    doc_token = doc_res["access_token"]

    # Patient
    pat_res = client.post("/auth/register/patient", json={
        "email": f"pat_{uuid.uuid4().hex[:6]}@example.com",
        "password": "Password123!",
        "full_name": "Patient X"
    }).json()
    pat_id = pat_res["user"]["profile"]["id"]

    # Unverified doctor attempting to access patient record must be rejected with 403
    access_res = client.get(
        f"/doctors/me/patients/{pat_id}",
        headers={"Authorization": f"Bearer {doc_token}"}
    )
    assert access_res.status_code == 403
    assert "pending" in access_res.json()["detail"].lower() or "verification" in access_res.json()["detail"].lower()

def test_admin_doctor_verification_workflow(client):
    # Register Admin directly
    db = TestingSessionLocal()
    from backend.app.core.security import hash_password
    admin_user = User(
        email=f"admin_{uuid.uuid4().hex[:6]}@anemiawatch.org",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
        account_status="active",
        email_verified=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    db.close()

    admin_login = client.post("/auth/login", json={
        "email": admin_user.email,
        "password": "AdminPass123!"
    }).json()
    admin_token = admin_login["access_token"]

    # Register Pending Doctor
    doc_res = client.post("/auth/register/doctor", json={
        "email": f"doc_to_approve_{uuid.uuid4().hex[:6]}@example.com",
        "password": "DocPassword123!",
        "full_name": "Dr. Will Approve",
        "medical_registration_number": f"REG-{uuid.uuid4().hex[:6]}",
        "qualification": "MD",
        "specialization": "Cardiology",
        "hospital_or_clinic": "City Hospital"
    }).json()
    doc_id = doc_res["user"]["doctor_info"]["id"]
    doc_token = doc_res["access_token"]

    # Check pending list
    pending_list = client.get("/admin/doctors/pending", headers={"Authorization": f"Bearer {admin_token}"})
    assert pending_list.status_code == 200
    assert any(d["id"] == doc_id for d in pending_list.json()["doctors"])

    # Approve Doctor
    appr_res = client.post(f"/admin/doctors/{doc_id}/approve", headers={"Authorization": f"Bearer {admin_token}"})
    assert appr_res.status_code == 200
    assert appr_res.json()["verification_status"] == "approved"

    # Now verified doctor checks profile
    doc_profile = client.get("/doctors/me", headers={"Authorization": f"Bearer {doc_token}"})
    assert doc_profile.status_code == 200
    assert doc_profile.json()["verification_status"] == "approved"

def test_consent_based_access_and_revocation(client):
    # 1. Admin setup
    db = TestingSessionLocal()
    from backend.app.core.security import hash_password
    admin_user = User(
        email=f"admin_consent_{uuid.uuid4().hex[:6]}@anemiawatch.org",
        password_hash=hash_password("AdminPass123!"),
        role="admin",
        account_status="active",
        email_verified=True
    )
    db.add(admin_user)
    db.commit()
    admin_token = client.post("/auth/login", json={"email": admin_user.email, "password": "AdminPass123!"}).json()["access_token"]

    # 2. Approved Doctor
    doc_res = client.post("/auth/register/doctor", json={
        "email": f"doc_consent_{uuid.uuid4().hex[:6]}@example.com",
        "password": "DocPassword123!",
        "full_name": "Dr. Consent Check",
        "medical_registration_number": f"REG-{uuid.uuid4().hex[:6]}",
        "qualification": "MD",
        "specialization": "Hematology",
        "hospital_or_clinic": "Mercy Hospital"
    }).json()
    doc_id = doc_res["user"]["doctor_info"]["id"]
    doc_token = doc_res["access_token"]
    client.post(f"/admin/doctors/{doc_id}/approve", headers={"Authorization": f"Bearer {admin_token}"})

    # 3. Patient
    pat_res = client.post("/auth/register/patient", json={
        "email": f"pat_consent_{uuid.uuid4().hex[:6]}@example.com",
        "password": "Password123!",
        "full_name": "Consent Granter"
    }).json()
    pat_id = pat_res["user"]["profile"]["id"]
    pat_token = pat_res["access_token"]

    # Doctor accessing patient BEFORE consent -> 403 Forbidden
    pre_consent = client.get(f"/doctors/me/patients/{pat_id}", headers={"Authorization": f"Bearer {doc_token}"})
    assert pre_consent.status_code == 403
    assert "consent" in pre_consent.json()["detail"].lower()

    # Patient grants consent
    grant_res = client.post(
        "/patients/me/consents",
        headers={"Authorization": f"Bearer {pat_token}"},
        json={
            "consent_type": "DOCTOR_ACCESS",
            "purpose": "Anemia Monitoring & Clinical Advice",
            "doctor_id": doc_id
        }
    )
    assert grant_res.status_code == 200

    # Doctor accessing patient AFTER consent -> 200 OK
    post_consent = client.get(f"/doctors/me/patients/{pat_id}", headers={"Authorization": f"Bearer {doc_token}"})
    assert post_consent.status_code == 200
    assert post_consent.json()["patient"]["full_name"] == "Consent Granter"

    # Patient revokes consent
    doc_list = client.get("/patients/me/doctors", headers={"Authorization": f"Bearer {pat_token}"}).json()
    consent_id = doc_list["authorized_doctors"][0]["consent_id"]
    
    rev_res = client.delete(f"/patients/me/consents/{consent_id}", headers={"Authorization": f"Bearer {pat_token}"})
    assert rev_res.status_code == 200

    # Doctor accessing patient AFTER revocation -> 403 Forbidden
    after_rev = client.get(f"/doctors/me/patients/{pat_id}", headers={"Authorization": f"Bearer {doc_token}"})
    assert after_rev.status_code == 403

# ─────────────────────────────────────────────────────────────────────────────
# 3. SECURITY & AUDIT TESTS
# ─────────────────────────────────────────────────────────────────────────────
def test_sql_injection_defense(client):
    sql_injection_payload = "' OR '1'='1"
    res = client.post("/auth/login", json={
        "email": sql_injection_payload,
        "password": "password"
    })
    # Must fail safely with 401 or 422, never 500 SQL syntax error
    assert res.status_code in [400, 401, 422]

def test_audit_log_generated(client):
    email = f"audit_check_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/auth/register/patient", json={
        "email": email,
        "password": "Password123!",
        "full_name": "Audit Tracked"
    })

    db = TestingSessionLocal()
    log = db.query(AuditLog).filter(AuditLog.action == "REGISTER_PATIENT_SUCCESS").first()
    assert log is not None
    assert log.status == "SUCCESS"
    db.close()
