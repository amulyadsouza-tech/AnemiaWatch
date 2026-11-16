from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List

from backend.app.database import get_db
from backend.app.models.schema import User, Patient, Doctor, DoctorPatient, Screening, Consent
from backend.app.schemas.patient import PatientProfileUpdateRequest, ConsentCreateRequest
from backend.app.core.permissions import get_current_user, get_current_patient, log_audit

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.get("/me")
def get_my_profile(
    patient: Patient = Depends(get_current_patient),
    user: User = Depends(get_current_user)
):
    return {
        "id": patient.id,
        "user_id": user.id,
        "email": user.email,
        "full_name": patient.full_name,
        "date_of_birth": patient.date_of_birth,
        "age": patient.age,
        "sex": patient.sex,
        "phone_number": patient.phone_number,
        "phone": patient.phone_number,
        "address": patient.address,
        "pregnancy_status": patient.pregnancy_status,
        "is_pregnant": patient.pregnancy_status,
        "emergency_contact": patient.emergency_contact,
        "created_at": patient.created_at.isoformat()
    }

@router.put("/me")
def update_my_profile(
    req: PatientProfileUpdateRequest,
    patient: Patient = Depends(get_current_patient),
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    if req.full_name is not None and req.full_name.strip():
        patient.full_name = req.full_name.strip()
    if req.date_of_birth is not None:
        patient.date_of_birth = req.date_of_birth
    if req.age is not None:
        patient.age = req.age
    if req.sex is not None:
        patient.sex = req.sex
    if req.phone_number is not None:
        patient.phone_number = req.phone_number
    elif req.phone is not None:
        patient.phone_number = req.phone
    if req.address is not None:
        patient.address = req.address
    if req.pregnancy_status is not None:
        patient.pregnancy_status = req.pregnancy_status
    elif req.is_pregnant is not None:
        patient.pregnancy_status = req.is_pregnant
    if req.emergency_contact is not None:
        patient.emergency_contact = req.emergency_contact

    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)

    log_audit(db, "PATIENT_PROFILE_UPDATED", user_id=user.id, resource_type="patient", resource_id=patient.id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "message": "Profile updated successfully.",
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "age": patient.age,
            "sex": patient.sex,
            "pregnancy_status": patient.pregnancy_status,
            "is_pregnant": patient.pregnancy_status,
            "phone_number": patient.phone_number,
            "phone": patient.phone_number
        }
    }

@router.get("/me/screenings")
def get_my_screenings(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    screenings = db.query(Screening).filter(
        Screening.patient_id == patient.id
    ).order_by(Screening.created_at.desc()).all()

    results = []
    for s in screenings:
        results.append({
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
            "model_version": s.model_version,
            "created_at": s.created_at.isoformat()
        })
    return {"status": "success", "count": len(results), "screenings": results}

@router.get("/doctors/available")
def get_available_doctors(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    """Returns all verified doctors available for consent grant."""
    all_approved = db.query(Doctor).filter(Doctor.verification_status == "approved").all()
    return {
        "status": "success",
        "doctors": [
            {
                "doctor_id": d.id,
                "full_name": d.full_name,
                "specialization": d.specialization,
                "hospital_or_clinic": d.hospital_or_clinic,
                "qualification": d.qualification
            }
            for d in all_approved
        ]
    }

@router.get("/me/doctors")
def get_authorized_doctors(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    """
    Returns:
    1. Active doctor assignments granted by this patient.
    2. List of approved doctors available to grant consent to.
    """
    assignments = db.query(DoctorPatient).filter(
        DoctorPatient.patient_id == patient.id,
        DoctorPatient.access_status == "active"
    ).all()

    authorized = []
    authorized_doc_ids = set()
    for a in assignments:
        doc = a.doctor
        authorized_doc_ids.add(doc.id)
        authorized.append({
            "consent_id": a.id,
            "doctor_id": doc.id,
            "full_name": doc.full_name,
            "specialization": doc.specialization,
            "hospital_or_clinic": doc.hospital_or_clinic,
            "granted_at": a.granted_at.isoformat(),
            "expires_at": a.expires_at.isoformat() if a.expires_at else None
        })

    # Available approved doctors
    all_approved = db.query(Doctor).filter(Doctor.verification_status == "approved").all()
    available = []
    for d in all_approved:
        if d.id not in authorized_doc_ids:
            available.append({
                "doctor_id": d.id,
                "full_name": d.full_name,
                "specialization": d.specialization,
                "hospital_or_clinic": d.hospital_or_clinic,
                "qualification": d.qualification
            })

    return {
        "status": "success",
        "authorized_doctors": authorized,
        "available_doctors": available
    }

@router.get("/me/consents")
def get_consents(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    consents = db.query(Consent).filter(
        Consent.patient_id == patient.id
    ).order_by(Consent.created_at.desc()).all()

    return {
        "status": "success",
        "consents": [
            {
                "id": c.id,
                "consent_type": c.consent_type,
                "consent_status": c.consent_status,
                "purpose": c.purpose,
                "granted_at": c.granted_at.isoformat(),
                "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None
            }
            for c in consents
        ]
    }

@router.post("/me/consents")
def grant_consent(
    req: ConsentCreateRequest,
    patient: Patient = Depends(get_current_patient),
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    
    # Create General Consent entry
    consent = Consent(
        patient_id=patient.id,
        consent_type=req.consent_type,
        consent_status="active",
        purpose=req.purpose.strip(),
        granted_at=now
    )
    db.add(consent)

    # If granting access to a specific doctor:
    if req.doctor_id:
        doc = db.query(Doctor).filter(Doctor.id == req.doctor_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Doctor not found.")
        if doc.verification_status != "approved":
            raise HTTPException(status_code=400, detail="Cannot grant access to an unverified doctor.")

        # Check existing assignment
        existing = db.query(DoctorPatient).filter(
            DoctorPatient.doctor_id == doc.id,
            DoctorPatient.patient_id == patient.id
        ).first()

        if existing:
            existing.access_status = "active"
            existing.revoked_at = None
            existing.granted_at = now
        else:
            dp = DoctorPatient(
                doctor_id=doc.id,
                patient_id=patient.id,
                access_status="active",
                granted_by=user.id,
                granted_at=now
            )
            db.add(dp)

    db.commit()
    db.refresh(consent)

    log_audit(db, "CONSENT_GRANTED", user_id=user.id, resource_type="consent", resource_id=consent.id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "message": "Consent recorded and permissions updated successfully.",
        "consent": {
            "id": consent.id,
            "consent_type": consent.consent_type,
            "consent_status": consent.consent_status,
            "purpose": consent.purpose,
            "granted_at": consent.granted_at.isoformat()
        }
    }

@router.delete("/me/consents/{consent_id}")
def revoke_consent(
    consent_id: str,
    patient: Patient = Depends(get_current_patient),
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    
    # 1. Check if it's a doctor assignment id
    dp = db.query(DoctorPatient).filter(
        DoctorPatient.id == consent_id,
        DoctorPatient.patient_id == patient.id
    ).first()
    
    if dp:
        dp.access_status = "revoked"
        dp.revoked_at = now
        db.commit()
        log_audit(db, "DOCTOR_ACCESS_REVOKED", user_id=user.id, resource_type="doctor_patient", resource_id=dp.id, status="SUCCESS", request=request)
        return {"status": "success", "message": "Doctor access successfully revoked."}

    # 2. Or a standard Consent record
    consent = db.query(Consent).filter(
        Consent.id == consent_id,
        Consent.patient_id == patient.id
    ).first()

    if not consent:
        raise HTTPException(status_code=404, detail="Consent record not found.")

    consent.consent_status = "withdrawn"
    consent.withdrawn_at = now
    db.commit()

    log_audit(db, "CONSENT_WITHDRAWN", user_id=user.id, resource_type="consent", resource_id=consent.id, status="SUCCESS", request=request)
    return {"status": "success", "message": "Consent successfully withdrawn."}
