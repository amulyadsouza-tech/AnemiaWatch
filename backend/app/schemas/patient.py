from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PatientProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=120)
    sex: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    pregnancy_status: Optional[bool] = None
    emergency_contact: Optional[str] = None
    # Backward compat
    is_pregnant: Optional[bool] = None
    phone: Optional[str] = None

class ConsentCreateRequest(BaseModel):
    consent_type: str = Field(default="DATA_SHARING") # 'DATA_SHARING', 'DOCTOR_ACCESS', 'RESEARCH'
    purpose: str = Field(..., min_length=3)
    doctor_id: Optional[str] = None # When granting access to a specific doctor

class ConsentResponse(BaseModel):
    id: str
    consent_type: str
    consent_status: str
    purpose: str
    granted_at: datetime
    withdrawn_at: Optional[datetime] = None

class MedicalHistoryCreateRequest(BaseModel):
    relevant_medical_information: Optional[str] = None
    notes: Optional[str] = None
