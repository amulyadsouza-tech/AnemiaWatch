from pydantic import BaseModel, Field
from typing import Optional

class DoctorVerificationRequest(BaseModel):
    action: Optional[str] = Field(None, pattern="^(approve|reject)$")
    approved: Optional[bool] = None  # Used by unified /verify endpoint
    verification_notes: Optional[str] = None
    reason: Optional[str] = None

class UserStatusUpdateRequest(BaseModel):
    account_status: str = Field(..., pattern="^(active|suspended|inactive|pending)$")
    reason: Optional[str] = None
