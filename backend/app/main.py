import os
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.database import engine, Base, SessionLocal, init_db
from backend.app.core.config import settings
from backend.app.core.security import hash_password
from backend.app.models.schema import User, Patient, Doctor, DoctorPatient
from backend.app.routers import auth, patients, doctors, admin, screening
from backend.app.services.ml_engine import (
    conj_regressor, conj_classifier, nail_regressor, conj_meta, nail_meta
)

# Initialize database schema
init_db()

def _seed_production_roles_and_test_accounts():
    """
    Seeds initial system roles:
    1. System Administrator: admin@anemiawatch.local / admin1234
    2. Verified Doctor: doctor@test.com / doctor1234
    3. Test Patient: test@gmail.com / test1234 (with active consent granted to test doctor)
    """
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        # 1. Admin
        admin_user = db.query(User).filter(User.email == "admin@anemiawatch.local").first()
        if not admin_user:
            admin_user = User(
                email="admin@anemiawatch.local",
                password_hash=hash_password("admin1234"),
                role="admin",
                account_status="active",
                email_verified=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        # 2. Approved Doctor
        doc_user = db.query(User).filter(User.email == "doctor@test.com").first()
        if not doc_user:
            doc_user = User(
                email="doctor@test.com",
                password_hash=hash_password("doctor1234"),
                role="doctor",
                account_status="active",
                email_verified=True
            )
            db.add(doc_user)
            db.flush()
            
            doc_profile = Doctor(
                user_id=doc_user.id,
                full_name="Dr. Test Doctor",
                medical_registration_number="REG-MED-88421",
                qualification="MBBS, MD (Hematology)",
                specialization="Hematology & Primary Care",
                hospital_or_clinic="Central Teaching Hospital",
                experience="10 years",
                phone_number="+1-555-019-2831",
                verification_status="approved",
                verified_by=admin_user.id,
                verified_at=now
            )
            db.add(doc_profile)
            db.commit()
            db.refresh(doc_user)
        elif doc_user.doctor and doc_user.doctor.verification_status != "approved":
            doc_user.doctor.verification_status = "approved"
            db.commit()

        # 3. Patient with granted doctor access
        pat_user = db.query(User).filter(User.email == "test@gmail.com").first()
        if not pat_user:
            pat_user = User(
                email="test@gmail.com",
                password_hash=hash_password("test1234"),
                role="patient",
                account_status="active",
                email_verified=True
            )
            db.add(pat_user)
            db.flush()
            
            pat_profile = Patient(
                user_id=pat_user.id,
                full_name="Test Patient",
                age=24,
                sex="female",
                pregnancy_status=False,
                phone_number="+1-555-012-3456"
            )
            db.add(pat_profile)
            db.commit()
            db.refresh(pat_user)

        # Ensure Doctor-Patient assignment exists between test patient and test doctor
        if pat_user.patient and doc_user.doctor:
            assignment = db.query(DoctorPatient).filter(
                DoctorPatient.doctor_id == doc_user.doctor.id,
                DoctorPatient.patient_id == pat_user.patient.id
            ).first()
            if not assignment:
                assignment = DoctorPatient(
                    doctor_id=doc_user.doctor.id,
                    patient_id=pat_user.patient.id,
                    access_status="active",
                    granted_by=pat_user.id,
                    granted_at=now
                )
                db.add(assignment)
                db.commit()
    except Exception as e:
        db.rollback()
        print(f"Notice: Account seeding handled ({e})")
    finally:
        db.close()

_seed_production_roles_and_test_accounts()

app = FastAPI(
    title="AnemiaWatch Clinical API",
    description="Production-grade AI-Assisted Anemia Screening, RBAC & Medical Audit Platform",
    version=settings.VERSION
)

# ─────────────────────────────────────────────────────────────────────────────
# CORS CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app" if settings.ALLOWED_ORIGINS != ["*"] else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# MOUNT API ROUTERS (Both prefixed with /api and direct root for compatibility)
# ─────────────────────────────────────────────────────────────────────────────
# Auth
app.include_router(auth.router, prefix="/api")
app.include_router(auth.router)

# Patients
app.include_router(patients.router, prefix="/api")
app.include_router(patients.router)

# Doctors
app.include_router(doctors.router, prefix="/api")
app.include_router(doctors.router)

# Admin
app.include_router(admin.router, prefix="/api")
app.include_router(admin.router)

# Screening (ML Engine)
app.include_router(screening.router)
app.include_router(screening.router, prefix="", tags=["Screening-Root"])

# ─────────────────────────────────────────────────────────────────────────────
# BACKWARD COMPATIBILITY ENDPOINTS (For legacy doctor dashboard calls)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/api/doctor/dashboard")
def legacy_doctor_dashboard(
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db)
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Requires doctor role.")
    
    doc = user.doctor
    if not doc or doc.verification_status != "approved":
        return {
            "status": "pending_verification",
            "message": "Doctor account pending administrator verification.",
            "metrics": {
                "total_patients": 0,
                "total_screenings": 0,
                "anemic_count": 0,
                "normal_count": 0,
                "severe_cases_flagged": 0
            },
            "recent_screenings": []
        }

    # Fetch authorized patients
    assignments = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doc.id,
        DoctorPatient.access_status == "active"
    ).all()
    pat_ids = [a.patient_id for a in assignments]

    from backend.app.models.schema import Screening
    scrs = db.query(Screening).filter(Screening.patient_id.in_(pat_ids)).all() if pat_ids else []
    
    anemic = sum(1 for s in scrs if s.is_anemic)
    severe = sum(1 for s in scrs if s.category == "Severe Anemia")
    
    recent = sorted(scrs, key=lambda s: s.created_at, reverse=True)[:6]
    recent_list = [
        {
            "id": s.id,
            "patient_id": s.patient_id,
            "patient_name": s.patient.full_name if s.patient else "Patient",
            "screening_type": s.screening_type,
            "estimated_hb": s.hemoglobin_estimate,
            "unit": s.unit,
            "category": s.category,
            "confidence": s.confidence,
            "quality_status": s.image_quality,
            "created_at": s.created_at.isoformat()
        } for s in recent
    ]

    return {
        "status": "success",
        "metrics": {
            "total_patients": len(pat_ids),
            "total_screenings": len(scrs),
            "anemic_count": anemic,
            "normal_count": max(0, len(scrs) - anemic),
            "severe_cases_flagged": severe
        },
        "recent_screenings": recent_list
    }

@app.get("/api/doctor/patients")
def legacy_doctor_patients(
    search: str = None,
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(auth.get_db)
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Requires doctor role.")
    return doctors.list_authorized_patients(search=search, doctor=doctors.get_approved_doctor(user, db), db=db)

@app.get("/api/doctor/patient/{patient_id}")
def legacy_doctor_patient_detail(
    patient_id: str,
    user: User = Depends(auth.get_current_user),
    request: Request = None,
    db: Session = Depends(auth.get_db)
):
    if user.role != "doctor":
        raise HTTPException(status_code=403, detail="Requires doctor role.")
    doc = doctors.get_approved_doctor(user, db)
    return doctors.get_authorized_patient_detail(patient_id=patient_id, doctor=doc, user=user, request=request, db=db)

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health")
@app.get("/api/health")
def health_check(db: Session = Depends(auth.get_db)):
    db_connected = False
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception:
        db_connected = False

    return {
        "status": "healthy" if db_connected else "degraded",
        "service": "AnemiaWatch Clinical Backend",
        "version": settings.VERSION,
        "database": "connected" if db_connected else "error",
        "models": {
            "conjunctiva_regressor_loaded": conj_regressor is not None,
            "conjunctiva_classifier_loaded": conj_classifier is not None,
            "nail_regressor_loaded": nail_regressor is not None,
            "conjunctiva_metrics": conj_meta,
            "nail_metrics": nail_meta
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# SPA STATIC SERVING (When built into frontend/dist)
# ─────────────────────────────────────────────────────────────────────────────
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
ASSETS_DIR = os.path.join(DIST_DIR, "assets")

if os.path.exists(DIST_DIR):
    if os.path.exists(ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
    async def serve_spa(request: Request, full_path: str):
        if full_path.startswith("api/") or full_path.startswith("api") or full_path.startswith("auth") or full_path.startswith("patients") or full_path.startswith("doctors") or full_path.startswith("admin"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        if request.method != "GET":
            raise HTTPException(status_code=404, detail="Endpoint not found")
        file_path = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
