import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="patient") # 'patient' or 'doctor'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    profile = relationship("PatientProfile", back_populates="user", uselist=False)
    screenings = relationship("Screening", back_populates="patient")

class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    age = Column(Integer, default=25)
    sex = Column(String, default="female") # 'male' or 'female'
    is_pregnant = Column(Boolean, default=False)
    blood_type = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    medical_notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="profile")

class Screening(Base):
    __tablename__ = "screenings"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    screening_type = Column(String, nullable=False) # 'nail' or 'conjunctiva'
    original_image_path = Column(String, nullable=False)
    processed_image_path = Column(String, nullable=False)
    
    estimated_hb = Column(Float, nullable=False)
    unit = Column(String, default="g/dL")
    confidence = Column(Float, nullable=False)
    category = Column(String, nullable=False) # 'Normal', 'Mild Anemia', 'Moderate Anemia', 'Severe Anemia'
    is_anemic = Column(Boolean, default=False)
    normal_min = Column(Float, default=12.0)
    normal_range_text = Column(String, nullable=False)
    
    erythema_index = Column(Float, nullable=True)
    color_stats_json = Column(Text, nullable=True)
    quality_score = Column(Integer, default=85)
    quality_status = Column(String, default="Optimal")
    
    recommendations_json = Column(Text, nullable=True)
    model_version = Column(String, default="v1.0")
    validation_status = Column(String, default="Validated")
    pdf_report_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    patient = relationship("User", back_populates="screenings")

class Article(Base):
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    category = Column(String, default="Education")
    summary = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String, nullable=True)
    read_time = Column(String, default="3 min")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
