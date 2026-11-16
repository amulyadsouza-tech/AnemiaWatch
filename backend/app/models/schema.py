import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

# ─────────────────────────────────────────────────────────────────────────────
# A. USERS TABLE
# ─────────────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="patient", nullable=False) # 'patient', 'doctor', 'admin'
    account_status = Column(String(20), default="active", nullable=False) # 'active', 'inactive', 'suspended', 'pending'
    email_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="user", uselist=False, cascade="all, delete-orphan")
    doctor = relationship("Doctor", back_populates="user", uselist=False, cascade="all, delete-orphan", foreign_keys="Doctor.user_id")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    @property
    def full_name(self) -> str:
        if self.patient:
            return self.patient.full_name
        if self.doctor:
            return self.doctor.full_name
        return self.email.split("@")[0]

# ─────────────────────────────────────────────────────────────────────────────
# B. PATIENTS TABLE
# ─────────────────────────────────────────────────────────────────────────────
class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(String(20), nullable=True)
    age = Column(Integer, nullable=True)
    sex = Column(String(20), default="female", nullable=False) # 'female', 'male', 'other'
    phone_number = Column(String(50), nullable=True)
    address = Column(Text, nullable=True)
    pregnancy_status = Column(Boolean, default=False, nullable=False)
    emergency_contact = Column(String(255), nullable=True)
    profile_completed = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="patient")
    screenings = relationship("Screening", back_populates="patient", cascade="all, delete-orphan")
    medical_histories = relationship("MedicalHistory", back_populates="patient", cascade="all, delete-orphan")
    consents = relationship("Consent", back_populates="patient", cascade="all, delete-orphan")
    doctor_accesses = relationship("DoctorPatient", back_populates="patient", cascade="all, delete-orphan")

# ─────────────────────────────────────────────────────────────────────────────
# C. DOCTORS TABLE
# ─────────────────────────────────────────────────────────────────────────────
class Doctor(Base):
    __tablename__ = "doctors"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    medical_registration_number = Column(String(100), unique=True, index=True, nullable=False)
    qualification = Column(String(255), nullable=False)
    specialization = Column(String(255), nullable=False)
    hospital_or_clinic = Column(String(255), nullable=False)
    experience = Column(String(50), nullable=True)
    phone_number = Column(String(50), nullable=True)
    verification_status = Column(String(20), default="pending", nullable=False) # 'pending', 'approved', 'rejected'
    verified_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="doctor", foreign_keys=[user_id])
    patient_accesses = relationship("DoctorPatient", back_populates="doctor", cascade="all, delete-orphan")

# ─────────────────────────────────────────────────────────────────────────────
# D. DOCTOR_PATIENT (CONSENT-BASED ACCESS TABLE)
# ─────────────────────────────────────────────────────────────────────────────
class DoctorPatient(Base):
    __tablename__ = "doctor_patient"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    doctor_id = Column(String(36), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    access_status = Column(String(20), default="active", nullable=False) # 'active', 'revoked', 'expired'
    granted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    granted_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    doctor = relationship("Doctor", back_populates="patient_accesses")
    patient = relationship("Patient", back_populates="doctor_accesses")

    __table_args__ = (
        Index("idx_doctor_patient_lookup", "doctor_id", "patient_id", "access_status"),
    )

# ─────────────────────────────────────────────────────────────────────────────
# E. SCREENINGS TABLE (CONNECTED TO ML PIPELINE)
# ─────────────────────────────────────────────────────────────────────────────
class Screening(Base):
    __tablename__ = "screenings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    screening_type = Column(String(50), nullable=False) # 'nail' / 'nail_bed' or 'conjunctiva' / 'eyelid'
    hemoglobin_estimate = Column(Float, nullable=True)
    unit = Column(String(20), default="g/dL", nullable=False)
    confidence = Column(Float, nullable=True)
    category = Column(String(50), nullable=True) # 'Normal', 'Mild Anemia', 'Moderate Anemia', 'Severe Anemia'
    is_anemic = Column(Boolean, default=False, nullable=False)
    normal_min = Column(Float, default=12.0)
    normal_range_text = Column(String(100), default="12.0 - 16.0 g/dL")
    prediction_result = Column(String(100), nullable=True)
    model_name = Column(String(100), default="AnemiaWatch-ML", nullable=False)
    model_version = Column(String(50), default="v1.0", nullable=False)
    image_quality = Column(String(50), default="Optimal", nullable=False)
    quality_score = Column(Integer, default=85, nullable=False)
    screening_status = Column(String(20), default="completed", nullable=False) # 'completed', 'failed', 'flagged'
    
    erythema_index = Column(Float, nullable=True)
    color_stats_json = Column(Text, nullable=True)
    recommendations_json = Column(Text, nullable=True)
    original_image_path = Column(String(500), nullable=True)
    processed_image_path = Column(String(500), nullable=True)
    pdf_report_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False, index=True)
    
    # Relationships
    patient = relationship("Patient", back_populates="screenings")

    # Compatibility alias for code expecting s.estimated_hb and s.quality_status
    @property
    def estimated_hb(self) -> float:
        return self.hemoglobin_estimate or 0.0

    @estimated_hb.setter
    def estimated_hb(self, val: float):
        self.hemoglobin_estimate = val

    @property
    def quality_status(self) -> str:
        return self.image_quality

    @quality_status.setter
    def quality_status(self, val: str):
        self.image_quality = val

    @property
    def validation_status(self) -> str:
        return "Validated"

# ─────────────────────────────────────────────────────────────────────────────
# F. MEDICAL_HISTORY TABLE
# ─────────────────────────────────────────────────────────────────────────────
class MedicalHistory(Base):
    __tablename__ = "medical_history"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    relevant_medical_information = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    
    # Relationships
    patient = relationship("Patient", back_populates="medical_histories")

# ─────────────────────────────────────────────────────────────────────────────
# G. REFRESH_TOKENS TABLE
# ─────────────────────────────────────────────────────────────────────────────
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    device_information = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

# ─────────────────────────────────────────────────────────────────────────────
# H. AUDIT_LOGS TABLE
# ─────────────────────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=utc_now, nullable=False, index=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    status = Column(String(20), default="SUCCESS", nullable=False) # 'SUCCESS', 'FAILURE', 'DENIED'

# ─────────────────────────────────────────────────────────────────────────────
# I. CONSENTS TABLE
# ─────────────────────────────────────────────────────────────────────────────
class Consent(Base):
    __tablename__ = "consents"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(50), nullable=False) # 'DATA_SHARING', 'DOCTOR_ACCESS', 'RESEARCH'
    consent_status = Column(String(20), default="active", nullable=False) # 'active', 'withdrawn', 'expired'
    granted_at = Column(DateTime, default=utc_now, nullable=False)
    withdrawn_at = Column(DateTime, nullable=True)
    purpose = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    
    # Relationships
    patient = relationship("Patient", back_populates="consents")

# ─────────────────────────────────────────────────────────────────────────────
# J. ARTICLES TABLE (EDUCATIONAL HEALTH CONTENT)
# ─────────────────────────────────────────────────────────────────────────────
class Article(Base):
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), default="Education")
    summary = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(255), nullable=True)
    read_time = Column(String(50), default="3 min")
    created_at = Column(DateTime, default=utc_now, nullable=False)
