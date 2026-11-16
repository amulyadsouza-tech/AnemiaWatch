from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class DoctorProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    qualification: Optional[str] = None
    specialization: Optional[str] = None
    hospital_or_clinic: Optional[str] = None
    experience: Optional[str] = None
    phone_number: Optional[str] = None

class ClinicalNoteRequest(BaseModel):
    notes: str = Field(..., min_length=1)

class DoctorResponse(BaseModel):
    id: str
    full_name: str
    medical_registration_number: str
    qualification: str
    specialization: str
    hospital_or_clinic: str
    experience: Optional[str] = None
    phone_number: Optional[str] = None
    verification_status: str
    created_at: datetime
