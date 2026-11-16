from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional

from backend.app.database import get_db
from backend.app.models.schema import User, Patient, Doctor, RefreshToken
from backend.app.schemas.auth import (
    PatientRegisterRequest, DoctorRegisterRequest, LoginRequest,
    RefreshTokenRequest, ChangePasswordRequest, ForgotPasswordRequest,
    ResetPasswordRequest, TokenResponse, UserResponse
)
from backend.app.core.security import (
    hash_password, verify_password, validate_password_strength,
    create_access_token, generate_refresh_token, hash_token,
    decode_token
)
from backend.app.core.permissions import get_current_user, log_audit
from backend.app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

def _build_user_dict(user: User) -> dict:
    profile_data = {}
    if user.patient:
        p = user.patient
        profile_data = {
            "id": p.id,
            "full_name": p.full_name,
            "age": p.age,
            "sex": p.sex,
            "is_pregnant": p.pregnancy_status,
            "pregnancy_status": p.pregnancy_status,
            "phone": p.phone_number,
            "phone_number": p.phone_number,
            "date_of_birth": p.date_of_birth,
            "address": p.address,
            "emergency_contact": p.emergency_contact
        }
    doctor_info = None
    if user.doctor:
        d = user.doctor
        doctor_info = {
            "id": d.id,
            "full_name": d.full_name,
            "medical_registration_number": d.medical_registration_number,
            "qualification": d.qualification,
            "specialization": d.specialization,
            "hospital_or_clinic": d.hospital_or_clinic,
            "experience": d.experience,
            "phone_number": d.phone_number,
            "verification_status": d.verification_status
        }
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "account_status": user.account_status,
        "email_verified": user.email_verified,
        "profile": profile_data,
        "doctor_info": doctor_info
    }

def to_naive_utc(dt):
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

# ─────────────────────────────────────────────────────────────────────────────
# PATIENT REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/register/patient")
@router.post("/register")
def register_patient(
    req: PatientRegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    email = req.email.lower().strip()
    
    # 1. Check duplicate email
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        log_audit(db, "REGISTER_PATIENT_DUPLICATE_EMAIL", resource_type="user", resource_id=email, status="DENIED", request=request)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered. Please sign in or use another email."
        )

    # 2. Validate password strength
    is_valid_pw, pw_err = validate_password_strength(req.password)
    if not is_valid_pw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_err)

    # 3. Create User & Patient within atomic transaction
    try:
        user = User(
            email=email,
            password_hash=hash_password(req.password),
            role="patient",
            account_status="active",
            email_verified=True # Auto-verify for active triage access
        )
        db.add(user)
        db.flush() # Flush to populate user.id

        preg_status = req.pregnancy_status if req.pregnancy_status is not None else (req.is_pregnant or False)
        phone = req.phone_number or req.phone or None

        patient = Patient(
            user_id=user.id,
            full_name=req.full_name.strip(),
            date_of_birth=req.date_of_birth,
            age=req.age or 25,
            sex=req.sex or "female",
            phone_number=phone,
            address=req.address,
            pregnancy_status=preg_status,
            emergency_contact=req.emergency_contact
        )
        db.add(patient)

        # Issue tokens
        access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
        raw_refresh, token_hash, exp_time = generate_refresh_token()
        
        refresh_entry = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=exp_time,
            device_information=request.headers.get("user-agent", "")[:250]
        )
        db.add(refresh_entry)
        
        db.commit()
        db.refresh(user)
        db.refresh(patient)
        
        log_audit(db, "REGISTER_PATIENT_SUCCESS", user_id=user.id, resource_type="user", resource_id=user.id, status="SUCCESS", request=request)
        
        return {
            "status": "success",
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "user": _build_user_dict(user)
        }
    except Exception as e:
        db.rollback()
        log_audit(db, "REGISTER_PATIENT_FAILURE", resource_type="user", resource_id=email, status="FAILURE", request=request)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed due to an internal error: {str(e)}"
        )

# ─────────────────────────────────────────────────────────────────────────────
# DOCTOR REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/register/doctor")
def register_doctor(
    req: DoctorRegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    email = req.email.lower().strip()
    
    # Check duplicate email
    if db.query(User).filter(User.email == email).first():
        log_audit(db, "REGISTER_DOCTOR_DUPLICATE_EMAIL", resource_type="user", resource_id=email, status="DENIED", request=request)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered. Please sign in or use another email."
        )

    # Check duplicate registration number
    reg_num = req.medical_registration_number.strip().upper()
    if db.query(Doctor).filter(Doctor.medical_registration_number == reg_num).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A doctor with this medical registration number is already registered."
        )

    is_valid_pw, pw_err = validate_password_strength(req.password)
    if not is_valid_pw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_err)

    try:
        user = User(
            email=email,
            password_hash=hash_password(req.password),
            role="doctor",
            account_status="active",
            email_verified=True
        )
        db.add(user)
        db.flush()

        doctor = Doctor(
            user_id=user.id,
            full_name=req.full_name.strip(),
            medical_registration_number=reg_num,
            qualification=req.qualification.strip(),
            specialization=req.specialization.strip(),
            hospital_or_clinic=req.hospital_or_clinic.strip(),
            experience=req.experience,
            phone_number=req.phone_number,
            verification_status="pending" # Strictly requires admin verification
        )
        db.add(doctor)

        access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
        raw_refresh, token_hash, exp_time = generate_refresh_token()
        
        refresh_entry = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=exp_time,
            device_information=request.headers.get("user-agent", "")[:250]
        )
        db.add(refresh_entry)

        db.commit()
        db.refresh(user)
        db.refresh(doctor)

        log_audit(db, "REGISTER_DOCTOR_SUCCESS", user_id=user.id, resource_type="doctor", resource_id=doctor.id, status="SUCCESS", request=request)

        return {
            "status": "success",
            "message": "Doctor registration submitted successfully. Your account is pending administrator verification.",
            "access_token": access_token,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "user": _build_user_dict(user)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Doctor registration failed: {str(e)}"
        )

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/login")
def login(
    req: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    email = req.email.lower().strip()
    now = datetime.now(timezone.utc)
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        log_audit(db, "LOGIN_FAILED_UNKNOWN_EMAIL", resource_type="user", resource_id=email, status="FAILURE", request=request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    # Check lockout
    if user.locked_until and to_naive_utc(user.locked_until) > to_naive_utc(now):
        remaining_mins = int((to_naive_utc(user.locked_until) - to_naive_utc(now)).total_seconds() / 60) + 1
        log_audit(db, "LOGIN_ATTEMPT_LOCKED_ACCOUNT", user_id=user.id, resource_type="user", resource_id=user.id, status="DENIED", request=request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is temporarily locked due to multiple failed login attempts. Please try again in {remaining_mins} minutes."
        )

    # Check account status
    if user.account_status == "suspended":
        log_audit(db, "LOGIN_ATTEMPT_SUSPENDED_ACCOUNT", user_id=user.id, status="DENIED", request=request)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is suspended. Please contact support.")
    elif user.account_status == "inactive":
        log_audit(db, "LOGIN_ATTEMPT_INACTIVE_ACCOUNT", user_id=user.id, status="DENIED", request=request)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")

    # Verify password
    if not verify_password(req.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
            db.commit()
            log_audit(db, "ACCOUNT_LOCKED_FAILED_LOGINS", user_id=user.id, status="DENIED", request=request)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Maximum login attempts exceeded. Account is locked for {settings.LOCKOUT_DURATION_MINUTES} minutes."
            )
        db.commit()
        log_audit(db, "LOGIN_FAILED_INVALID_PASSWORD", user_id=user.id, status="FAILURE", request=request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    # Upgrade password to Argon2id if was legacy PBKDF2 hash
    if not user.password_hash.startswith("$argon2"):
        try:
            user.password_hash = hash_password(req.password)
        except Exception:
            pass

    # Success: reset lockout counters & update last_login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = now

    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    raw_refresh, token_hash, exp_time = generate_refresh_token()
    
    refresh_entry = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=exp_time,
        device_information=request.headers.get("user-agent", "")[:250]
    )
    db.add(refresh_entry)
    db.commit()

    log_audit(db, "LOGIN_SUCCESS", user_id=user.id, resource_type="user", resource_id=user.id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "user": _build_user_dict(user)
    }

# ─────────────────────────────────────────────────────────────────────────────
# REFRESH TOKEN ROTATION
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/refresh")
def refresh_token(
    req: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    incoming_hash = hash_token(req.refresh_token.strip())
    
    stored = db.query(RefreshToken).filter(RefreshToken.token_hash == incoming_hash).first()
    if not stored:
        log_audit(db, "REFRESH_TOKEN_INVALID", status="DENIED", request=request)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")

    if stored.revoked_at is not None:
        # Potential token reuse attack! Revoke all tokens for this user for security
        db.query(RefreshToken).filter(RefreshToken.user_id == stored.user_id).update({"revoked_at": now})
        db.commit()
        log_audit(db, "REFRESH_TOKEN_REUSE_DETECTED", user_id=stored.user_id, status="DENIED", request=request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Security alert: Token has already been used or revoked. Please sign in again."
        )

    if to_naive_utc(stored.expires_at) < to_naive_utc(now):
        stored.revoked_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired.")

    user = stored.user
    if not user or user.account_status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active.")

    # Rotate refresh token: revoke current, issue new
    stored.revoked_at = now

    new_access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    new_raw_refresh, new_token_hash, new_exp = generate_refresh_token()
    
    new_refresh_entry = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=new_exp,
        device_information=request.headers.get("user-agent", "")[:250]
    )
    db.add(new_refresh_entry)
    db.commit()

    log_audit(db, "REFRESH_TOKEN_ROTATED", user_id=user.id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "access_token": new_access_token,
        "refresh_token": new_raw_refresh,
        "token_type": "bearer",
        "user": _build_user_dict(user)
    }

# ─────────────────────────────────────────────────────────────────────────────
# LOGOUT
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/logout")
def logout(
    req: Optional[RefreshTokenRequest] = None,
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    if req and req.refresh_token:
        token_hash = hash_token(req.refresh_token.strip())
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id,
            RefreshToken.token_hash == token_hash
        ).update({"revoked_at": now})
    else:
        # Revoke all active sessions for current user
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at == None
        ).update({"revoked_at": now})
        
    db.commit()
    log_audit(db, "LOGOUT_SUCCESS", user_id=user.id, status="SUCCESS", request=request)
    return {"status": "success", "message": "Successfully logged out and session revoked."}

# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD CHANGE
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    if not verify_password(req.current_password, user.password_hash):
        log_audit(db, "PASSWORD_CHANGE_INVALID_CURRENT", user_id=user.id, status="FAILURE", request=request)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect.")

    is_valid, err = validate_password_strength(req.new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    now = datetime.now(timezone.utc)
    user.password_hash = hash_password(req.new_password)
    user.updated_at = now
    
    # Invalidate all existing refresh tokens for security
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked_at == None
    ).update({"revoked_at": now})
    
    db.commit()
    log_audit(db, "PASSWORD_CHANGE_SUCCESS", user_id=user.id, status="SUCCESS", request=request)
    return {"status": "success", "message": "Password changed successfully. All previous sessions have been signed out."}

# ─────────────────────────────────────────────────────────────────────────────
# FORGOT / RESET PASSWORD
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/forgot-password")
def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    email = req.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    
    # Generic message to avoid email enumeration
    msg = "If an account exists for this email, password reset instructions have been dispatched."
    
    if user and user.account_status == "active":
        # Create a single-purpose short-lived password reset token (15 mins)
        reset_token = create_access_token(
            {"sub": user.id, "email": user.email, "type": "password_reset"},
            expires_delta=timedelta(minutes=15)
        )
        log_audit(db, "PASSWORD_RESET_REQUESTED", user_id=user.id, status="SUCCESS", request=request)
        # In a full mail setup, send email here. In local/preview, return or log safe status.
    else:
        log_audit(db, "PASSWORD_RESET_UNKNOWN_EMAIL", resource_id=email, status="DENIED", request=request)

    return {"status": "success", "message": msg}

@router.post("/reset-password")
def reset_password(
    req: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    payload = decode_token(req.token)
    if not payload or payload.get("type") != "password_reset" or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password reset token is invalid or has expired.")

    is_valid, err = validate_password_strength(req.new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    now = datetime.now(timezone.utc)
    user.password_hash = hash_password(req.new_password)
    user.updated_at = now
    
    # Revoke sessions
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).update({"revoked_at": now})
    db.commit()

    log_audit(db, "PASSWORD_RESET_SUCCESS", user_id=user.id, status="SUCCESS", request=request)
    return {"status": "success", "message": "Password reset successfully. You may now sign in with your new password."}

# ─────────────────────────────────────────────────────────────────────────────
# CURRENT USER INFO (/auth/me)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return _build_user_dict(user)

# ─────────────────────────────────────────────────────────────────────────────
# GUEST PREVIEW / ONBOARDING LOGIN (/auth/guest)
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/guest")
def guest_login(request: Request, db: Session = Depends(get_db)):
    guest_email = "guest@anemiawatch.local"
    user = db.query(User).filter(User.email == guest_email).first()
    if not user:
        user = User(
            email=guest_email,
            password_hash=hash_password("guest123456"),
            role="patient",
            account_status="active",
            email_verified=True
        )
        db.add(user)
        db.flush()
        
        patient = Patient(
            user_id=user.id,
            full_name="Guest Patient",
            age=24,
            sex="female",
            pregnancy_status=False
        )
        db.add(patient)
        db.commit()
        db.refresh(user)

    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    raw_refresh, token_hash, exp_time = generate_refresh_token()
    
    refresh_entry = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=exp_time,
        device_information=request.headers.get("user-agent", "")[:250]
    )
    db.add(refresh_entry)
    db.commit()

    log_audit(db, "GUEST_LOGIN", user_id=user.id, status="SUCCESS", request=request)
    return {
        "status": "success",
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "user": _build_user_dict(user)
    }
