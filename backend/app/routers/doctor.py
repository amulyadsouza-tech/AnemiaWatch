from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import json
import os

from backend.app.database import get_db
from backend.app.models.schema import User, PatientProfile, Screening
from backend.app.routers.auth import get_current_user

router = APIRouter(prefix="/api/doctor", tags=["Doctor Dashboard"])

def verify_doctor_role(user: User = Depends(get_current_user)):
    if user.role != "doctor":
        # Allow demo or doctor access
        # If user registered as patient, return 403
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor dashboard requires doctor or clinician role"
        )
    return user

@router.get("/dashboard")
def get_dashboard_summary(user: User = Depends(verify_doctor_role), db: Session = Depends(get_db)):
    """
    Overview statistics and recent screenings for the clinical dashboard.
    """
    total_patients = db.query(User).filter(User.role == "patient").count()
    total_screenings = db.query(Screening).count()
    anemic_count = db.query(Screening).filter(Screening.is_anemic == True).count()
    severe_count = db.query(Screening).filter(Screening.category == "Severe Anemia").count()
    
    # Recent 6 screenings
    recent_screenings = db.query(Screening).order_by(Screening.created_at.desc()).limit(6).all()
    recent_list = []
    for s in recent_screenings:
        p_name = s.patient.full_name if s.patient else "Patient"
        recent_list.append({
            "id": s.id,
            "patient_id": s.patient_id,
            "patient_name": p_name,
            "screening_type": s.screening_type,
            "estimated_hb": s.estimated_hb,
            "unit": s.unit,
            "category": s.category,
            "confidence": s.confidence,
            "quality_status": s.quality_status,
            "created_at": s.created_at.isoformat()
        })
        
    return {
        "status": "success",
        "metrics": {
            "total_patients": total_patients,
            "total_screenings": total_screenings,
            "anemic_count": anemic_count,
            "normal_count": max(0, total_screenings - anemic_count),
            "severe_cases_flagged": severe_count
        },
        "recent_screenings": recent_list
    }

@router.get("/patients")
def list_patients(
    search: Optional[str] = Query(None),
    user: User = Depends(verify_doctor_role),
    db: Session = Depends(get_db)
):
    """
    Lists patients with search filtering and their latest screening snapshot.
    """
    query = db.query(User).filter(User.role == "patient")
    if search:
        query = query.filter((User.full_name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")))
        
    patients = query.all()
    results = []
    for p in patients:
        latest_screening = db.query(Screening).filter(Screening.patient_id == p.id).order_by(Screening.created_at.desc()).first()
        screening_count = db.query(Screening).filter(Screening.patient_id == p.id).count()
        
        prof = p.profile
        results.append({
            "id": p.id,
            "full_name": p.full_name,
            "email": p.email,
            "age": prof.age if prof else 25,
            "sex": prof.sex if prof else "female",
            "is_pregnant": prof.is_pregnant if prof else False,
            "phone": prof.phone if prof else None,
            "total_screenings": screening_count,
            "latest_screening": {
                "id": latest_screening.id,
                "date": latest_screening.created_at.isoformat(),
                "hb": latest_screening.estimated_hb,
                "category": latest_screening.category,
                "method": latest_screening.screening_type
            } if latest_screening else None
        })
    return {"status": "success", "patients": results}

@router.get("/patient/{patient_id}")
def get_patient_profile_and_history(
    patient_id: int,
    user: User = Depends(verify_doctor_role),
    db: Session = Depends(get_db)
):
    """
    Returns full longitudinal history and clinical notes for an individual patient.
    """
    patient = db.query(User).filter(User.id == patient_id, User.role == "patient").first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
        
    screenings = db.query(Screening).filter(Screening.patient_id == patient_id).order_by(Screening.created_at.asc()).all()
    
    history = []
    for s in screenings:
        orig_name = os.path.basename(s.original_image_path)
        proc_name = os.path.basename(s.processed_image_path)
        parent_dir = os.path.basename(os.path.dirname(s.original_image_path))
        
        history.append({
            "id": s.id,
            "screening_type": s.screening_type,
            "estimated_hb": s.estimated_hb,
            "unit": s.unit,
            "confidence": s.confidence,
            "category": s.category,
            "is_anemic": s.is_anemic,
            "quality_status": s.quality_status,
            "original_image_url": f"/api/screening/file/{patient_id}/{parent_dir}/{orig_name}",
            "processed_image_url": f"/api/screening/file/{patient_id}/{parent_dir}/{proc_name}",
            "created_at": s.created_at.isoformat()
        })
        
    prof = patient.profile
    return {
        "status": "success",
        "patient": {
            "id": patient.id,
            "full_name": patient.full_name,
            "email": patient.email,
            "age": prof.age if prof else 25,
            "sex": prof.sex if prof else "female",
            "is_pregnant": prof.is_pregnant if prof else False,
            "blood_type": prof.blood_type if prof else None,
            "phone": prof.phone if prof else None,
            "medical_notes": prof.medical_notes if prof else None,
            "registered_at": patient.created_at.isoformat()
        },
        "history": history
    }
