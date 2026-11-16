from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

class PatientRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    role: Optional[str] = "patient"
    age: Optional[int] = Field(default=25, ge=0, le=120)
    date_of_birth: Optional[str] = None
    sex: Optional[str] = "female"
    pregnancy_status: Optional[bool] = False
    phone_number: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    # For backward-compat with old frontend fields:
    is_pregnant: Optional[bool] = None
    phone: Optional[str] = None
    blood_type: Optional[str] = None

class DoctorRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
    medical_registration_number: str = Field(..., min_length=3)
    qualification: str = Field(..., min_length=2)
    specialization: str = Field(..., min_length=2)
    hospital_or_clinic: str = Field(..., min_length=2)
    experience: Optional[str] = None
    phone_number: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    account_status: str
    email_verified: bool
    full_name: str
    created_at: Optional[datetime] = None
    profile: Optional[dict] = None
    doctor_info: Optional[dict] = None

class TokenResponse(BaseModel):
    status: str = "success"
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: dict
