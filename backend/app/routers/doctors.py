from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, List
import os

from backend.app.database import get_db
from backend.app.models.schema import User, Patient, Doctor, DoctorPatient, Screening, MedicalHistory
from backend.app.schemas.doctor import DoctorProfileUpdateRequest, ClinicalNoteRequest
from backend.app.core.permissions import (
    get_current_user, get_approved_doctor, verify_doctor_patient_consent, log_audit, require_role
)

router = APIRouter(prefix="/doctors", tags=["Doctors"])

@router.get("/me")
def get_my_doctor_profile(
    user: User = Depends(require_role(["doctor"])),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")
        
    return {
        "id": doctor.id,
        "user_id": user.id,
        "email": user.email,
        "full_name": doctor.full_name,
        "medical_registration_number": doctor.medical_registration_number,
        "qualification": doctor.qualification,
        "specialization": doctor.specialization,
        "hospital_or_clinic": doctor.hospital_or_clinic,
        "experience": doctor.experience,
        "phone_number": doctor.phone_number,
        "verification_status": doctor.verification_status,
        "created_at": doctor.created_at.isoformat()
    }

@router.put("/me")
def update_my_doctor_profile(
    req: DoctorProfileUpdateRequest,
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")

    if req.full_name is not None and req.full_name.strip():
        doctor.full_name = req.full_name.strip()
    if req.qualification is not None:
        doctor.qualification = req.qualification.strip()
    if req.specialization is not None:
        doctor.specialization = req.specialization.strip()
    if req.hospital_or_clinic is not None:
        doctor.hospital_or_clinic = req.hospital_or_clinic.strip()
    if req.experience is not None:
        doctor.experience = req.experience
    if req.phone_number is not None:
        doctor.phone_number = req.phone_number

    doctor.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doctor)

    log_audit(db, "DOCTOR_PROFILE_UPDATED", user_id=user.id, resource_type="doctor", resource_id=doctor.id, status="SUCCESS", request=request)
    return {"status": "success", "message": "Doctor profile updated."}

@router.get("/me/patients")
def list_authorized_patients(
    search: Optional[str] = Query(None),
    doctor: Doctor = Depends(get_approved_doctor),
    db: Session = Depends(get_db)
):
    """
    Returns ONLY patients who have granted active, non-expired access to this verified doctor.
    """
    assignments = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doctor.id,
        DoctorPatient.access_status == "active"
    ).all()

    patient_ids = [a.patient_id for a in assignments]
    if not patient_ids:
        return {"status": "success", "count": 0, "patients": []}

    query = db.query(Patient).filter(Patient.id.in_(patient_ids))
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(Patient.full_name.ilike(s))

    patients = query.all()
    results = []
    for p in patients:
        latest_screening = db.query(Screening).filter(
            Screening.patient_id == p.id
        ).order_by(Screening.created_at.desc()).first()

        total_scrs = db.query(Screening).filter(Screening.patient_id == p.id).count()

        results.append({
            "id": p.id,
            "full_name": p.full_name,
            "age": p.age,
            "sex": p.sex,
            "is_pregnant": p.pregnancy_status,
            "pregnancy_status": p.pregnancy_status,
            "phone": p.phone_number,
            "total_screenings": total_scrs,
            "latest_screening": {
                "id": latest_screening.id,
                "date": latest_screening.created_at.isoformat(),
                "hb": latest_screening.hemoglobin_estimate,
                "estimated_hb": latest_screening.hemoglobin_estimate,
                "category": latest_screening.category,
                "method": latest_screening.screening_type,
                "is_anemic": latest_screening.is_anemic
            } if latest_screening else None
        })

    return {"status": "success", "count": len(results), "patients": results}

@router.get("/me/patients/{patient_id}")
def get_authorized_patient_detail(
    patient_id: str,
    doctor: Doctor = Depends(get_approved_doctor),
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Enforces consent-based access check before returning patient clinical information.
    """
    verify_doctor_patient_consent(doctor, patient_id, db)

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    screenings = db.query(Screening).filter(
        Screening.patient_id == patient_id
    ).order_by(Screening.created_at.asc()).all()

    history = []
    for s in screenings:
        orig_name = os.path.basename(s.original_image_path) if s.original_image_path else ""
        proc_name = os.path.basename(s.processed_image_path) if s.processed_image_path else ""
        parent_dir = os.path.basename(os.path.dirname(s.original_image_path)) if s.original_image_path else ""

        history.append({
            "id": s.id,
            "screening_type": s.screening_type,
            "estimated_hb": s.hemoglobin_estimate,
            "hemoglobin_estimate": s.hemoglobin_estimate,
            "unit": s.unit,
            "confidence": s.confidence,
            "category": s.category,
            "is_anemic": s.is_anemic,
            "quality_status": s.image_quality,
            "original_image_url": f"/api/screening/file/{patient.user_id}/{parent_dir}/{orig_name}" if orig_name else "",
            "processed_image_url": f"/api/screening/file/{patient.user_id}/{parent_dir}/{proc_name}" if proc_name else "",
            "created_at": s.created_at.isoformat()
        })

    # Fetch notes & medical histories
    med_records = db.query(MedicalHistory).filter(
        MedicalHistory.patient_id == patient_id
    ).order_by(MedicalHistory.created_at.desc()).all()

    clinical_notes = [
        {
            "id": m.id,
            "notes": m.notes,
            "created_at": m.created_at.isoformat()
        } for m in med_records if m.notes
    ]

    log_audit(db, "DOCTOR_PATIENT_RECORD_ACCESSED", user_id=user.id, resource_type="patient", resource_id=patient_id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "age": patient.age,
            "sex": patient.sex,
            "is_pregnant": patient.pregnancy_status,
            "pregnancy_status": patient.pregnancy_status,
            "phone": patient.phone_number,
            "address": patient.address,
            "created_at": patient.created_at.isoformat()
        },
        "history": history,
        "clinical_notes": clinical_notes
    }

@router.get("/me/patients/{patient_id}/screenings")
def get_authorized_patient_screenings(
    patient_id: str,
    doctor: Doctor = Depends(get_approved_doctor),
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    verify_doctor_patient_consent(doctor, patient_id, db)

    screenings = db.query(Screening).filter(
        Screening.patient_id == patient_id
    ).order_by(Screening.created_at.desc()).all()

    log_audit(db, "DOCTOR_PATIENT_SCREENINGS_ACCESSED", user_id=user.id, resource_type="screening", resource_id=patient_id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "screenings": [
            {
                "id": s.id,
                "screening_type": s.screening_type,
                "hemoglobin_estimate": s.hemoglobin_estimate,
                "estimated_hb": s.hemoglobin_estimate,
                "unit": s.unit,
                "confidence": s.confidence,
                "category": s.category,
                "is_anemic": s.is_anemic,
                "quality_status": s.image_quality,
                "quality_score": s.quality_score,
                "created_at": s.created_at.isoformat()
            } for s in screenings
        ]
    }

@router.post("/me/patients/{patient_id}/notes")
def add_clinical_note(
    patient_id: str,
    req: ClinicalNoteRequest,
    doctor: Doctor = Depends(get_approved_doctor),
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    verify_doctor_patient_consent(doctor, patient_id, db)

    note_text = f"[Dr. {doctor.full_name} ({doctor.specialization})]: {req.notes.strip()}"
    med = MedicalHistory(
        patient_id=patient_id,
        notes=note_text
    )
    db.add(med)
    db.commit()
    db.refresh(med)

    log_audit(db, "CLINICAL_NOTE_ADDED", user_id=user.id, resource_type="medical_history", resource_id=med.id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "message": "Clinical note added successfully.",
        "note": {
            "id": med.id,
            "notes": med.notes,
            "created_at": med.created_at.isoformat()
        }
    }
