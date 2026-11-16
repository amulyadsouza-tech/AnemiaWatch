from fastapi import Depends, HTTPException, status, Header, Query, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from backend.app.database import get_db
from backend.app.models.schema import User, Patient, Doctor, DoctorPatient, AuditLog
from backend.app.core.security import decode_token

def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> User:
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ", 1)[1].strip()
    elif token:
        raw_token = token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )
    
    payload = decode_token(raw_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is expired or invalid"
        )
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found"
        )
        
    if user.account_status == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended. Please contact clinical administration."
        )
    elif user.account_status == "inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive."
        )

    return user

def require_role(allowed_roles: List[str]):
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {', '.join(allowed_roles)}"
            )
        return user
    return role_checker

def get_current_patient(
    user: User = Depends(require_role(["patient"])),
    db: Session = Depends(get_db)
) -> Patient:
    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    return patient

def get_approved_doctor(
    user: User = Depends(require_role(["doctor"])),
    db: Session = Depends(get_db)
) -> Doctor:
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
        
    if doctor.verification_status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Doctor account is {doctor.verification_status}. Patient medical records can only be accessed after administrator verification."
        )
    return doctor

def verify_doctor_patient_consent(doctor: Doctor, patient_id: str, db: Session) -> DoctorPatient:
    """
    Enforces consent-based access:
    Verifies that an active, non-revoked, non-expired DoctorPatient relationship exists.
    """
    now = datetime.now(timezone.utc)
    assignment = db.query(DoctorPatient).filter(
        DoctorPatient.doctor_id == doctor.id,
        DoctorPatient.patient_id == patient_id,
        DoctorPatient.access_status == "active"
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Patient has not granted access to this medical record or consent was revoked."
        )

    exp = assignment.expires_at
    if exp:
        if getattr(exp, "tzinfo", None) is not None:
            exp = exp.astimezone(timezone.utc).replace(tzinfo=None)
        cur = now.astimezone(timezone.utc).replace(tzinfo=None)
        if exp < cur:
            assignment.access_status = "expired"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access expired: The patient's consent period has ended."
            )

    return assignment

def log_audit(
    db: Session,
    action: str,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    status: str = "SUCCESS",
    request: Optional[Request] = None
):
    """
    Centralized audit logging for security and compliance.
    Does NOT log passwords, tokens, or raw medical images.
    """
    ip_addr = None
    ua = None
    if request:
        ip_addr = request.client.host if request.client else None
        ua = request.headers.get("user-agent", "")[:250]
        
    audit_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status,
        ip_address=ip_addr,
        user_agent=ua
    )
    db.add(audit_entry)
    try:
        db.commit()
    except Exception:
        db.rollback()
