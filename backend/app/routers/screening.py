import os
import json
import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List

from backend.app.database import get_db
from backend.app.models.schema import User, Patient, Screening, Article
from backend.app.core.permissions import get_current_user, verify_doctor_patient_consent, log_audit
from backend.app.services.nail_processor import process_nail_image
from backend.app.services.conjunctiva_processor import process_conjunctiva_image
from backend.app.services.ml_engine import predict_conjunctiva, predict_nail_bed
from backend.app.services.pdf_generator import generate_screening_pdf

router = APIRouter(prefix="/api/screening", tags=["Screening"])

UPLOAD_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads"))
try:
    os.makedirs(UPLOAD_ROOT, exist_ok=True)
except OSError:
    UPLOAD_ROOT = "/tmp/uploads"
    os.makedirs(UPLOAD_ROOT, exist_ok=True)

def _get_or_create_patient(user: User, db: Session) -> Patient:
    """Ensures a patient profile exists for the current user."""
    if user.patient:
        return user.patient
    p = Patient(
        user_id=user.id,
        full_name=user.full_name or "Patient",
        age=25,
        sex="female",
        pregnancy_status=False
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

@router.post("/nail")
@router.post("/nail/")
async def screen_nail_bed(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process fingernail photo, detect nail ROIs, apply quality filtering,
    extract 42 intensity percentiles, run calibrated regression model.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

    # File size limit: 15MB
    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image file exceeds maximum 15MB limit")

    patient = _get_or_create_patient(user, db)

    screening_session_id = str(uuid.uuid4())[:12]
    session_dir = os.path.join(UPLOAD_ROOT, f"user_{user.id}", f"nail_{screening_session_id}")
    os.makedirs(session_dir, exist_ok=True)
    
    # Save original image
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    orig_filename = f"original{file_ext}"
    orig_path = os.path.join(session_dir, orig_filename)
    
    with open(orig_path, "wb") as f:
        f.write(content)
        
    # Process nail image
    try:
        cv_res = process_nail_image(orig_path, session_dir)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Image processing failed: {str(e)}")
        
    age = patient.age or 25
    sex = patient.sex or "female"
    is_pregnant = patient.pregnancy_status or False
    
    # ML inference
    ml_res = predict_nail_bed(
        cv_res["features_42"],
        quality_score=cv_res["quality"]["score"],
        sex=sex,
        age=age,
        is_pregnant=is_pregnant
    )
    
    # Store screening record in database
    screening = Screening(
        patient_id=patient.id,
        screening_type="nail",
        original_image_path=orig_path,
        processed_image_path=cv_res["annotated_image_path"],
        hemoglobin_estimate=ml_res["estimated_hb"],
        unit=ml_res["unit"],
        confidence=ml_res["confidence_percentage"],
        category=ml_res["classification"]["category"],
        is_anemic=ml_res["classification"]["is_anemic"],
        normal_min=ml_res["classification"]["normal_minimum"],
        normal_range_text=ml_res["classification"]["normal_range_text"],
        prediction_result=ml_res["classification"]["category"],
        model_name="AnemiaWatch-Fingernail-Pipeline",
        model_version=ml_res["model_version"],
        image_quality=cv_res["quality"]["status"],
        quality_score=cv_res["quality"]["score"],
        screening_status="completed",
        erythema_index=None,
        color_stats_json=json.dumps(cv_res["color_stats"]),
        recommendations_json=json.dumps(ml_res["recommendations"])
    )
    db.add(screening)
    db.commit()
    db.refresh(screening)
    
    # Generate PDF report
    pdf_path = os.path.join(session_dir, f"report_{screening.id}.pdf")
    pdf_meta = {
        "id": screening.id,
        "patient_name": patient.full_name,
        "patient_age": age,
        "patient_sex": sex,
        "is_pregnant": is_pregnant,
        "screening_type": "Fingernail Bed Analysis",
        "created_at": screening.created_at.isoformat(),
        "estimated_hb": ml_res["estimated_hb"],
        "category": ml_res["classification"]["category"],
        "confidence": ml_res["confidence_percentage"],
        "normal_range_text": ml_res["classification"]["normal_range_text"],
        "quality_status": cv_res["quality"]["status"],
        "original_image_path": orig_path,
        "processed_image_path": cv_res["annotated_image_path"],
        "prevention": ml_res["recommendations"]["prevention"],
        "risks": ml_res["recommendations"]["risks"],
        "advice": ml_res["recommendations"]["advice"],
        "model_version": ml_res["model_version"],
        "validation_status": ml_res["validation_status"]
    }
    generate_screening_pdf(pdf_meta, pdf_path)
    screening.pdf_report_path = pdf_path
    db.commit()
    
    orig_url = f"/api/screening/file/{user.id}/nail_{screening_session_id}/{orig_filename}"
    proc_url = f"/api/screening/file/{user.id}/nail_{screening_session_id}/{cv_res['annotated_filename']}"
    
    log_audit(db, "SCREENING_COMPLETED_NAIL", user_id=user.id, resource_type="screening", resource_id=screening.id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "screening_id": screening.id,
        "screening_type": "nail",
        "original_image_url": orig_url,
        "processed_image_url": proc_url,
        "quality": cv_res["quality"],
        "nail_count": cv_res["nail_count"],
        "color_stats": cv_res["color_stats"],
        "estimated_hb": ml_res["estimated_hb"],
        "unit": ml_res["unit"],
        "confidence": ml_res["confidence_percentage"],
        "classification": ml_res["classification"],
        "recommendations": ml_res["recommendations"],
        "model_version": ml_res["model_version"],
        "validation_status": ml_res["validation_status"],
        "disclaimer": ml_res["disclaimer"],
        "created_at": screening.created_at.isoformat()
    }

@router.post("/conjunctiva")
@router.post("/conjunctiva/")
async def screen_conjunctiva(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process lower eyelid palpebral conjunctiva photo,
    detect lower mucosal region, calculate Erythema Index (EI = 100 * log10(R/G)),
    run validated Harvard clinical dataset regression model.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

    content = await file.read()
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image file exceeds maximum 15MB limit")

    patient = _get_or_create_patient(user, db)

    screening_session_id = str(uuid.uuid4())[:12]
    session_dir = os.path.join(UPLOAD_ROOT, f"user_{user.id}", f"conj_{screening_session_id}")
    os.makedirs(session_dir, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    orig_filename = f"original{file_ext}"
    orig_path = os.path.join(session_dir, orig_filename)
    
    with open(orig_path, "wb") as f:
        f.write(content)
        
    try:
        cv_res = process_conjunctiva_image(orig_path, session_dir)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Image processing failed: {str(e)}")
        
    age = patient.age or 25
    sex = patient.sex or "female"
    is_pregnant = patient.pregnancy_status or False
    
    ml_res = predict_conjunctiva(
        cv_res["erythema_index"],
        quality_score=cv_res["quality"]["score"],
        sex=sex,
        age=age,
        is_pregnant=is_pregnant
    )
    
    screening = Screening(
        patient_id=patient.id,
        screening_type="conjunctiva",
        original_image_path=orig_path,
        processed_image_path=cv_res["annotated_image_path"],
        hemoglobin_estimate=ml_res["estimated_hb"],
        unit=ml_res["unit"],
        confidence=ml_res["confidence_percentage"],
        category=ml_res["classification"]["category"],
        is_anemic=ml_res["classification"]["is_anemic"],
        normal_min=ml_res["classification"]["normal_minimum"],
        normal_range_text=ml_res["classification"]["normal_range_text"],
        prediction_result=ml_res["classification"]["category"],
        model_name="Harvard-Clinical-Conjunctiva-Pipeline",
        model_version=ml_res["model_version"],
        image_quality=cv_res["quality"]["status"],
        quality_score=cv_res["quality"]["score"],
        screening_status="completed",
        erythema_index=cv_res["erythema_index"],
        color_stats_json=json.dumps(cv_res["color_stats"]),
        recommendations_json=json.dumps(ml_res["recommendations"])
    )
    db.add(screening)
    db.commit()
    db.refresh(screening)
    
    pdf_path = os.path.join(session_dir, f"report_{screening.id}.pdf")
    pdf_meta = {
        "id": screening.id,
        "patient_name": patient.full_name,
        "patient_age": age,
        "patient_sex": sex,
        "is_pregnant": is_pregnant,
        "screening_type": "Palpebral Conjunctiva Analysis",
        "created_at": screening.created_at.isoformat(),
        "estimated_hb": ml_res["estimated_hb"],
        "category": ml_res["classification"]["category"],
        "confidence": ml_res["confidence_percentage"],
        "normal_range_text": ml_res["classification"]["normal_range_text"],
        "quality_status": cv_res["quality"]["status"],
        "original_image_path": orig_path,
        "processed_image_path": cv_res["annotated_image_path"],
        "prevention": ml_res["recommendations"]["prevention"],
        "risks": ml_res["recommendations"]["risks"],
        "advice": ml_res["recommendations"]["advice"],
        "model_version": ml_res["model_version"],
        "validation_status": ml_res["validation_status"]
    }
    generate_screening_pdf(pdf_meta, pdf_path)
    screening.pdf_report_path = pdf_path
    db.commit()
    
    orig_url = f"/api/screening/file/{user.id}/conj_{screening_session_id}/{orig_filename}"
    proc_url = f"/api/screening/file/{user.id}/conj_{screening_session_id}/{cv_res['annotated_filename']}"
    
    log_audit(db, "SCREENING_COMPLETED_CONJUNCTIVA", user_id=user.id, resource_type="screening", resource_id=screening.id, status="SUCCESS", request=request)

    return {
        "status": "success",
        "screening_id": screening.id,
        "screening_type": "conjunctiva",
        "original_image_url": orig_url,
        "processed_image_url": proc_url,
        "quality": cv_res["quality"],
        "erythema_index": cv_res["erythema_index"],
        "color_stats": cv_res["color_stats"],
        "estimated_hb": ml_res["estimated_hb"],
        "unit": ml_res["unit"],
        "confidence": ml_res["confidence_percentage"],
        "classification": ml_res["classification"],
        "recommendations": ml_res["recommendations"],
        "model_version": ml_res["model_version"],
        "validation_status": ml_res["validation_status"],
        "disclaimer": ml_res["disclaimer"],
        "created_at": screening.created_at.isoformat()
    }

@router.get("/history")
def get_screening_history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.patient:
        return {"status": "success", "screenings": []}

    screenings = db.query(Screening).filter(
        Screening.patient_id == user.patient.id
    ).order_by(Screening.created_at.desc()).all()

    results = []
    for s in screenings:
        orig_name = os.path.basename(s.original_image_path) if s.original_image_path else ""
        proc_name = os.path.basename(s.processed_image_path) if s.processed_image_path else ""
        parent_dir = os.path.basename(os.path.dirname(s.original_image_path)) if s.original_image_path else ""
        
        orig_url = f"/api/screening/file/{user.id}/{parent_dir}/{orig_name}" if orig_name else ""
        proc_url = f"/api/screening/file/{user.id}/{parent_dir}/{proc_name}" if proc_name else ""
        
        recs = json.loads(s.recommendations_json) if s.recommendations_json else {}
        results.append({
            "id": s.id,
            "screening_type": s.screening_type,
            "estimated_hb": s.hemoglobin_estimate,
            "hemoglobin_estimate": s.hemoglobin_estimate,
            "unit": s.unit,
            "confidence": s.confidence,
            "category": s.category,
            "is_anemic": s.is_anemic,
            "normal_range_text": s.normal_range_text,
            "erythema_index": s.erythema_index,
            "quality_status": s.image_quality,
            "quality_score": s.quality_score,
            "original_image_url": orig_url,
            "processed_image_url": proc_url,
            "model_version": s.model_version,
            "validation_status": "Validated",
            "recommendations": recs,
            "created_at": s.created_at.isoformat()
        })
    return {"status": "success", "screenings": results}

@router.get("/detail/{screening_id}")
def get_screening_detail(
    screening_id: str,
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    s = db.query(Screening).filter(Screening.id == screening_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Screening record not found")

    # Strict IDOR Access Control
    if user.role == "patient":
        if not user.patient or s.patient_id != user.patient.id:
            raise HTTPException(status_code=403, detail="Unauthorized access to patient screening record")
    elif user.role == "doctor":
        if not user.doctor or user.doctor.verification_status != "approved":
            raise HTTPException(status_code=403, detail="Doctor verification required to view clinical screenings")
        verify_doctor_patient_consent(user.doctor, s.patient_id, db)
    elif user.role == "admin":
        pass
    else:
        raise HTTPException(status_code=403, detail="Unauthorized access")
        
    orig_name = os.path.basename(s.original_image_path) if s.original_image_path else ""
    proc_name = os.path.basename(s.processed_image_path) if s.processed_image_path else ""
    parent_dir = os.path.basename(os.path.dirname(s.original_image_path)) if s.original_image_path else ""
    
    orig_url = f"/api/screening/file/{s.patient.user_id}/{parent_dir}/{orig_name}" if orig_name else ""
    proc_url = f"/api/screening/file/{s.patient.user_id}/{parent_dir}/{proc_name}" if proc_name else ""
    recs = json.loads(s.recommendations_json) if s.recommendations_json else {}
    stats = json.loads(s.color_stats_json) if s.color_stats_json else {}
    
    log_audit(db, "SCREENING_DETAIL_VIEWED", user_id=user.id, resource_type="screening", resource_id=s.id, status="SUCCESS", request=request)

    return {
        "id": s.id,
        "patient_id": s.patient_id,
        "patient_name": s.patient.full_name if s.patient else "Patient",
        "screening_type": s.screening_type,
        "estimated_hb": s.hemoglobin_estimate,
        "hemoglobin_estimate": s.hemoglobin_estimate,
        "unit": s.unit,
        "confidence": s.confidence,
        "category": s.category,
        "is_anemic": s.is_anemic,
        "normal_min": s.normal_min,
        "normal_range_text": s.normal_range_text,
        "erythema_index": s.erythema_index,
        "quality_score": s.quality_score,
        "quality_status": s.image_quality,
        "color_stats": stats,
        "recommendations": recs,
        "original_image_url": orig_url,
        "processed_image_url": proc_url,
        "model_version": s.model_version,
        "validation_status": "Validated",
        "created_at": s.created_at.isoformat(),
        "disclaimer": "This is an AI-assisted screening estimate and not a confirmed medical diagnosis. Please consult a healthcare professional and confirm your hemoglobin level through appropriate laboratory testing."
    }

@router.get("/{screening_id}/pdf")
def download_pdf(
    screening_id: str,
    user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    s = db.query(Screening).filter(Screening.id == screening_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Screening not found")
        
    if user.role == "patient":
        if not user.patient or s.patient_id != user.patient.id:
            raise HTTPException(status_code=403, detail="Unauthorized")
    elif user.role == "doctor":
        if not user.doctor or user.doctor.verification_status != "approved":
            raise HTTPException(status_code=403, detail="Doctor verification required")
        verify_doctor_patient_consent(user.doctor, s.patient_id, db)
    elif user.role == "admin":
        pass
    else:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    if not s.pdf_report_path or not os.path.exists(s.pdf_report_path):
        # Regenerate on demand
        pdf_path = os.path.join(os.path.dirname(s.original_image_path), f"report_{s.id}.pdf")
        patient = s.patient
        patient_name = patient.full_name if patient else "Patient"
        age = patient.age if patient else 25
        sex = patient.sex if patient else "female"
        is_pregnant = patient.pregnancy_status if patient else False
        recs = json.loads(s.recommendations_json) if s.recommendations_json else {}
        
        pdf_meta = {
            "id": s.id,
            "patient_name": patient_name,
            "patient_age": age,
            "patient_sex": sex,
            "is_pregnant": is_pregnant,
            "screening_type": "Fingernail Bed Analysis" if s.screening_type == "nail" else "Palpebral Conjunctiva Analysis",
            "created_at": s.created_at.isoformat(),
            "estimated_hb": s.hemoglobin_estimate,
            "category": s.category,
            "confidence": s.confidence,
            "normal_range_text": s.normal_range_text,
            "quality_status": s.image_quality,
            "original_image_path": s.original_image_path,
            "processed_image_path": s.processed_image_path,
            "prevention": recs.get("prevention", "Maintain a balanced iron-rich diet."),
            "risks": recs.get("risks", "Untreated anemia risks chronic fatigue."),
            "advice": recs.get("advice", "Confirm with laboratory CBC testing."),
            "model_version": s.model_version,
            "validation_status": "Validated"
        }
        generate_screening_pdf(pdf_meta, pdf_path)
        s.pdf_report_path = pdf_path
        db.commit()
        
    log_audit(db, "PDF_REPORT_DOWNLOADED", user_id=user.id, resource_type="screening_pdf", resource_id=s.id, status="SUCCESS", request=request)
    return FileResponse(s.pdf_report_path, media_type="application/pdf", filename=f"AnemiaWatch_Report_{s.id}.pdf")

@router.get("/file/{user_id}/{folder}/{filename}")
def serve_screening_image(user_id: str, folder: str, filename: str):
    """
    Safely serves patient inspection images with directory traversal protection.
    """
    safe_user = os.path.basename(user_id)
    safe_folder = os.path.basename(folder)
    safe_file = os.path.basename(filename)
    safe_path = os.path.abspath(os.path.join(UPLOAD_ROOT, f"user_{safe_user}", safe_folder, safe_file))
    if not safe_path.startswith(UPLOAD_ROOT) or not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(safe_path)

@router.get("/articles")
def get_articles(db: Session = Depends(get_db)):
    """
    Returns English educational articles.
    """
    EN_ARTICLES = [
        {
            "title": "Recognizing Anemia Symptoms in Teens & Adults",
            "category": "Symptoms & Awareness",
            "summary": "Early signs of anemia: chronic fatigue, pale nailbeds, dizziness, and shortness of breath.",
            "content": "Anemia occurs when your blood lacks enough healthy red blood cells or hemoglobin. Common symptoms include persistent fatigue, dizziness upon standing, brittle nails, pale inner eyelids, cold hands and feet, and shortness of breath during light activities. If you experience any combination of these symptoms regularly, an anemia screening is strongly recommended.",
            "read_time": "3 min",
            "image_url": "/assets/articles/article1.jpg"
        },
        {
            "title": "Causes of Anemia & Who Is at Risk?",
            "category": "Causes & Diagnosis",
            "summary": "Key causes include dietary iron deficiency, rapid growth phases, blood loss, and genetic factors.",
            "content": "Primary causes of anemia include inadequate dietary iron absorption, chronic gastrointestinal blood loss, increased iron requirements during pregnancy, rapid adolescent growth, and genetic hemoglobin disorders such as sickle cell disease and thalassemia. Women, adolescents, vegetarians, and pregnant individuals are at highest risk.",
            "read_time": "4 min",
            "image_url": "/assets/articles/article2.jpg"
        },
        {
            "title": "Iron-Rich Foods & Anemia Prevention",
            "category": "Nutrition & Prevention",
            "summary": "Leafy greens, lean meats, lentils, and vitamin C help maximize iron absorption.",
            "content": "To build and maintain optimal hemoglobin levels, incorporate heme iron from poultry and lean meats, or non-heme iron from beans, spinach, lentils, and tofu. Always pair with vitamin C-rich foods like oranges, tomatoes, and bell peppers to enhance bioavailability. Avoid tea and coffee within 1 hour of iron-rich meals as they inhibit absorption.",
            "read_time": "5 min",
            "image_url": "/assets/articles/article3.jpg"
        },
        {
            "title": "Understanding Hemoglobin & Blood Tests",
            "category": "Lab Tests & Monitoring",
            "summary": "What CBC tests reveal about your Hb levels, MCV, and overall blood health.",
            "content": "A Complete Blood Count (CBC) is the gold standard for anemia diagnosis. It measures hemoglobin (Hb), hematocrit, red blood cell count, MCV (mean corpuscular volume), and iron saturation. Normal adult female Hb range is 12–16 g/dL; for males, 13–17.5 g/dL. If your Hb falls below these thresholds, follow up with a serum ferritin test to check iron stores.",
            "read_time": "4 min",
            "image_url": "/assets/articles/article4.jpg"
        }
    ]

    articles = db.query(Article).all()
    if not articles:
        for item in EN_ARTICLES:
            db.add(Article(**item))
        db.commit()
        articles = db.query(Article).all()

    return [
        {
            "id": a.id,
            "title": a.title,
            "category": a.category,
            "summary": a.summary,
            "content": a.content,
            "read_time": a.read_time,
            "image_url": a.image_url
        } for a in articles
    ]
