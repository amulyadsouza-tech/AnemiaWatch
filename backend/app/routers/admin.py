from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional, List

from backend.app.database import get_db
from backend.app.models.schema import User, Doctor, Patient, AuditLog
from backend.app.schemas.admin import DoctorVerificationRequest, UserStatusUpdateRequest
from backend.app.core.permissions import get_current_user, require_role, log_audit

router = APIRouter(prefix="/admin", tags=["Administration"])

@router.get("/doctors/pending")
def list_pending_doctors(
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    pending = db.query(Doctor).filter(Doctor.verification_status == "pending").all()
    return {
        "status": "success",
        "count": len(pending),
        "doctors": [
            {
                "id": d.id,
                "user_id": d.user_id,
                "full_name": d.full_name,
                "email": d.user.email if d.user else "",
                "medical_registration_number": d.medical_registration_number,
                "qualification": d.qualification,
                "specialization": d.specialization,
                "hospital_or_clinic": d.hospital_or_clinic,
                "experience": d.experience,
                "phone_number": d.phone_number,
                "verification_status": d.verification_status,
                "submitted_at": d.created_at.isoformat()
            } for d in pending
        ]
    }

@router.post("/doctors/{doctor_id}/approve")
def approve_doctor(
    doctor_id: str,
    admin: User = Depends(require_role(["admin"])),
    request: Request = None,
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found.")

    now = datetime.now(timezone.utc)
    doctor.verification_status = "approved"
    doctor.verified_by = admin.id
    doctor.verified_at = now
    doctor.updated_at = now

    db.commit()
    log_audit(db, "DOCTOR_VERIFIED_APPROVED", user_id=admin.id, resource_type="doctor", resource_id=doctor.id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "message": f"Doctor {doctor.full_name} has been verified and approved.",
        "doctor_id": doctor.id,
        "verification_status": "approved"
    }

@router.post("/doctors/{doctor_id}/reject")
def reject_doctor(
    doctor_id: str,
    admin: User = Depends(require_role(["admin"])),
    request: Request = None,
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found.")

    now = datetime.now(timezone.utc)
    doctor.verification_status = "rejected"
    doctor.verified_by = admin.id
    doctor.verified_at = now
    doctor.updated_at = now

    db.commit()
    log_audit(db, "DOCTOR_VERIFIED_REJECTED", user_id=admin.id, resource_type="doctor", resource_id=doctor.id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "message": f"Doctor {doctor.full_name} registration has been rejected.",
        "doctor_id": doctor.id,
        "verification_status": "rejected"
    }

@router.post("/doctors/{doctor_id}/verify")
def verify_doctor(
    doctor_id: str,
    req: DoctorVerificationRequest,
    admin: User = Depends(require_role(["admin"])),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Unified verify endpoint used by admin frontend: approve or reject based on req.approved."""
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor record not found.")

    now = datetime.now(timezone.utc)
    new_status = "approved" if req.approved else "rejected"
    doctor.verification_status = new_status
    doctor.verified_by = admin.id
    doctor.verified_at = now
    doctor.updated_at = now

    db.commit()
    log_audit(db, f"DOCTOR_VERIFIED_{new_status.upper()}", user_id=admin.id, resource_type="doctor", resource_id=doctor.id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "message": f"Doctor {doctor.full_name} has been {new_status}.",
        "doctor_id": doctor.id,
        "verification_status": new_status
    }

@router.get("/stats")
def admin_stats(
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    from backend.app.models.schema import Patient, Screening
    total_users = db.query(User).count()
    total_patients = db.query(Patient).count()
    pending_doctors = db.query(Doctor).filter(Doctor.verification_status == "pending").count()
    approved_doctors = db.query(Doctor).filter(Doctor.verification_status == "approved").count()
    total_screenings = db.query(Screening).count()
    return {
        "status": "success",
        "total_users": total_users,
        "total_patients": total_patients,
        "pending_doctors": pending_doctors,
        "approved_doctors": approved_doctors,
        "total_screenings": total_screenings
    }

@router.get("/users")
def list_users(
    role: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if status_filter:
        q = q.filter(User.account_status == status_filter)

    users = q.order_by(User.created_at.desc()).limit(limit).all()

    return {
        "status": "success",
        "count": len(users),
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "account_status": u.account_status,
                "email_verified": u.email_verified,
                "full_name": u.full_name,
                "created_at": u.created_at.isoformat(),
                "last_login": u.last_login.isoformat() if u.last_login else None
            } for u in users
        ]
    }

@router.post("/users/{user_id}/status")
def update_user_status(
    user_id: str,
    req: UserStatusUpdateRequest,
    admin: User = Depends(require_role(["admin"])),
    request: Request = None,
    db: Session = Depends(get_db)
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot alter own account status.")

    old_status = target.account_status
    target.account_status = req.account_status
    target.updated_at = datetime.now(timezone.utc)
    db.commit()

    log_audit(
        db,
        f"USER_STATUS_CHANGED_{req.account_status.upper()}",
        user_id=admin.id,
        resource_type="user",
        resource_id=target.id,
        status="SUCCESS",
        request=request
    )

    return {
        "status": "success",
        "message": f"User status changed from {old_status} to {req.account_status}."
    }

@router.get("/audit-logs")
def view_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = Query(None),
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))

    logs = q.order_by(AuditLog.timestamp.desc()).limit(limit).all()

    return {
        "status": "success",
        "count": len(logs),
        "logs": [
            {
                "id": l.id,
                "user_id": l.user_id,
                "action": l.action,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "timestamp": l.timestamp.isoformat(),
                "status": l.status,
                "ip_address": l.ip_address
            } for l in logs
        ]
    }
