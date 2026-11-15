from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from backend.app.database import get_db
from backend.app.models.schema import User, PatientProfile
from backend.app.utils.security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: Optional[str] = "patient"
    age: Optional[int] = 25
    sex: Optional[str] = "female"
    is_pregnant: Optional[bool] = False
    blood_type: Optional[str] = None
    phone: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    is_pregnant: Optional[bool] = None
    blood_type: Optional[str] = None
    phone: Optional[str] = None
    medical_notes: Optional[str] = None

def _get_or_create_guest_user(db: Session) -> User:
    guest_email = "guest@anemiawatch.local"
    user = db.query(User).filter(User.email == guest_email).first()
    if not user:
        user = User(
            email=guest_email,
            hashed_password=hash_password("guest123"),
            full_name="Guest Patient",
            role="patient"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        profile = PatientProfile(
            user_id=user.id,
            age=24,
            sex="female",
            is_pregnant=False,
            blood_type="O+",
            phone=""
        )
        db.add(profile)
        db.commit()
        db.refresh(user)
    return user

def get_current_user(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> User:
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1]
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authentication token")
    
    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is expired or invalid")
    
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user

@router.post("/guest")
def guest_login(db: Session = Depends(get_db)):
    user = _get_or_create_guest_user(db)
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    profile_data = {
        "age": user.profile.age if user.profile else 24,
        "sex": user.profile.sex if user.profile else "female",
        "is_pregnant": user.profile.is_pregnant if user.profile else False,
        "blood_type": user.profile.blood_type if user.profile else "O+",
        "phone": user.profile.phone if user.profile else ""
    }
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "profile": profile_data
        }
    }

@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")
        
    user = User(
        email=req.email.lower().strip(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name.strip(),
        role=req.role if req.role in ["patient", "doctor"] else "patient"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    profile = PatientProfile(
        user_id=user.id,
        age=req.age or 25,
        sex=req.sex or "female",
        is_pregnant=req.is_pregnant or False,
        blood_type=req.blood_type,
        phone=req.phone
    )
    db.add(profile)
    db.commit()
    
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "profile": {
                "age": profile.age,
                "sex": profile.sex,
                "is_pregnant": profile.is_pregnant,
                "blood_type": profile.blood_type,
                "phone": profile.phone
            }
        }
    }

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower().strip()).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    profile_data = {}
    if user.profile:
        profile_data = {
            "age": user.profile.age,
            "sex": user.profile.sex,
            "is_pregnant": user.profile.is_pregnant,
            "blood_type": user.profile.blood_type,
            "phone": user.profile.phone,
            "medical_notes": user.profile.medical_notes
        }
        
    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "profile": profile_data
        }
    }

@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    profile_data = {}
    if user.profile:
        profile_data = {
            "age": user.profile.age,
            "sex": user.profile.sex,
            "is_pregnant": user.profile.is_pregnant,
            "blood_type": user.profile.blood_type,
            "phone": user.profile.phone,
            "medical_notes": user.profile.medical_notes
        }
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "created_at": user.created_at.isoformat(),
        "profile": profile_data
    }

@router.put("/profile")
def update_profile(req: ProfileUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.full_name:
        user.full_name = req.full_name
    if not user.profile:
        user.profile = PatientProfile(user_id=user.id)
        db.add(user.profile)
        
    if req.age is not None:
        user.profile.age = req.age
    if req.sex is not None:
        user.profile.sex = req.sex
    if req.is_pregnant is not None:
        user.profile.is_pregnant = req.is_pregnant
    if req.blood_type is not None:
        user.profile.blood_type = req.blood_type
    if req.phone is not None:
        user.profile.phone = req.phone
    if req.medical_notes is not None:
        user.profile.medical_notes = req.medical_notes
        
    db.commit()
    db.refresh(user)
    return {
        "status": "success",
        "message": "Profile updated successfully",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role
        },
        "profile": {
            "age": user.profile.age,
            "sex": user.profile.sex,
            "is_pregnant": user.profile.is_pregnant,
            "blood_type": user.profile.blood_type,
            "phone": user.profile.phone,
            "medical_notes": user.profile.medical_notes
        }
    }
