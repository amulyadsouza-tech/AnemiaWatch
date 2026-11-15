import os
import json
import uuid
import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List

from backend.app.database import get_db
from backend.app.models.schema import User, Screening, Article
from backend.app.routers.auth import get_current_user
from backend.app.services.nail_processor import process_nail_image
from backend.app.services.conjunctiva_processor import process_conjunctiva_image
from backend.app.services.ml_engine import predict_conjunctiva, predict_nail_bed
from backend.app.services.pdf_generator import generate_screening_pdf

router = APIRouter(prefix="/api/screening", tags=["Screening"])

IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

if IS_SERVERLESS:
    UPLOAD_ROOT = "/tmp/uploads"
else:
    UPLOAD_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "uploads"))
    try:
        os.makedirs(UPLOAD_ROOT, exist_ok=True)
    except OSError:
        UPLOAD_ROOT = "/tmp/uploads"

os.makedirs(UPLOAD_ROOT, exist_ok=True)

@router.post("/nail")
async def screen_nail_bed(
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
        
    screening_session_id = str(uuid.uuid4())[:12]
    session_dir = os.path.join(UPLOAD_ROOT, f"user_{user.id}", f"nail_{screening_session_id}")
    os.makedirs(session_dir, exist_ok=True)
    
    # Save original image
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    orig_filename = f"original{file_ext}"
    orig_path = os.path.join(session_dir, orig_filename)
    
    with open(orig_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    # Process nail image
    try:
        cv_res = process_nail_image(orig_path, session_dir)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Image processing failed: {str(e)}")
        
    # User demographic context
    age = user.profile.age if user.profile else 25
    sex = user.profile.sex if user.profile else "female"
    is_pregnant = user.profile.is_pregnant if user.profile else False
    
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
        patient_id=user.id,
        screening_type="nail",
        original_image_path=orig_path,
        processed_image_path=cv_res["annotated_image_path"],
        estimated_hb=ml_res["estimated_hb"],
        unit=ml_res["unit"],
        confidence=ml_res["confidence_percentage"],
        category=ml_res["classification"]["category"],
        is_anemic=ml_res["classification"]["is_anemic"],
        normal_min=ml_res["classification"]["normal_minimum"],
        normal_range_text=ml_res["classification"]["normal_range_text"],
        erythema_index=None,
        color_stats_json=json.dumps(cv_res["color_stats"]),
        quality_score=cv_res["quality"]["score"],
        quality_status=cv_res["quality"]["status"],
        recommendations_json=json.dumps(ml_res["recommendations"]),
        model_version=ml_res["model_version"],
        validation_status=ml_res["validation_status"]
    )
    db.add(screening)
    db.commit()
    db.refresh(screening)
    
    # Generate PDF report
    pdf_path = os.path.join(session_dir, f"report_{screening.id}.pdf")
    pdf_meta = {
        "id": screening.id,
        "patient_name": user.full_name,
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
    
    # Relative image URLs for frontend display
    orig_url = f"/api/screening/file/{user.id}/nail_{screening_session_id}/{orig_filename}"
    proc_url = f"/api/screening/file/{user.id}/nail_{screening_session_id}/{cv_res['annotated_filename']}"
    
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
async def screen_conjunctiva(
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
        
    screening_session_id = str(uuid.uuid4())[:12]
    session_dir = os.path.join(UPLOAD_ROOT, f"user_{user.id}", f"conj_{screening_session_id}")
    os.makedirs(session_dir, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    orig_filename = f"original{file_ext}"
    orig_path = os.path.join(session_dir, orig_filename)
    
    with open(orig_path, "wb") as f:
        content = await file.read()
        f.write(content)
        
    try:
        cv_res = process_conjunctiva_image(orig_path, session_dir)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Image processing failed: {str(e)}")
        
    age = user.profile.age if user.profile else 25
    sex = user.profile.sex if user.profile else "female"
    is_pregnant = user.profile.is_pregnant if user.profile else False
    
    ml_res = predict_conjunctiva(
        cv_res["erythema_index"],
        quality_score=cv_res["quality"]["score"],
        sex=sex,
        age=age,
        is_pregnant=is_pregnant
    )
    
    screening = Screening(
        patient_id=user.id,
        screening_type="conjunctiva",
        original_image_path=orig_path,
        processed_image_path=cv_res["annotated_image_path"],
        estimated_hb=ml_res["estimated_hb"],
        unit=ml_res["unit"],
        confidence=ml_res["confidence_percentage"],
        category=ml_res["classification"]["category"],
        is_anemic=ml_res["classification"]["is_anemic"],
        normal_min=ml_res["classification"]["normal_minimum"],
        normal_range_text=ml_res["classification"]["normal_range_text"],
        erythema_index=cv_res["erythema_index"],
        color_stats_json=json.dumps(cv_res["color_stats"]),
        quality_score=cv_res["quality"]["score"],
        quality_status=cv_res["quality"]["status"],
        recommendations_json=json.dumps(ml_res["recommendations"]),
        model_version=ml_res["model_version"],
        validation_status=ml_res["validation_status"]
    )
    db.add(screening)
    db.commit()
    db.refresh(screening)
    
    pdf_path = os.path.join(session_dir, f"report_{screening.id}.pdf")
    pdf_meta = {
        "id": screening.id,
        "patient_name": user.full_name,
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
    """
    Returns historical screening records for current patient.
    """
    screenings = db.query(Screening).filter(Screening.patient_id == user.id).order_by(Screening.created_at.desc()).all()
    results = []
    for s in screenings:
        orig_name = os.path.basename(s.original_image_path)
        proc_name = os.path.basename(s.processed_image_path)
        parent_dir = os.path.basename(os.path.dirname(s.original_image_path))
        
        orig_url = f"/api/screening/file/{user.id}/{parent_dir}/{orig_name}"
        proc_url = f"/api/screening/file/{user.id}/{parent_dir}/{proc_name}"
        
        recs = json.loads(s.recommendations_json) if s.recommendations_json else {}
        results.append({
            "id": s.id,
            "screening_type": s.screening_type,
            "estimated_hb": s.estimated_hb,
            "unit": s.unit,
            "confidence": s.confidence,
            "category": s.category,
            "is_anemic": s.is_anemic,
            "normal_range_text": s.normal_range_text,
            "erythema_index": s.erythema_index,
            "quality_status": s.quality_status,
            "quality_score": s.quality_score,
            "original_image_url": orig_url,
            "processed_image_url": proc_url,
            "model_version": s.model_version,
            "validation_status": s.validation_status,
            "recommendations": recs,
            "created_at": s.created_at.isoformat()
        })
    return {"status": "success", "screenings": results}

@router.get("/detail/{screening_id}")
def get_screening_detail(screening_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieves full detail of a screening.
    Ensures privacy: patients cannot view others' screenings.
    """
    s = db.query(Screening).filter(Screening.id == screening_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Screening record not found")
        
    if user.role != "doctor" and s.patient_id != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to patient screening record")
        
    orig_name = os.path.basename(s.original_image_path)
    proc_name = os.path.basename(s.processed_image_path)
    parent_dir = os.path.basename(os.path.dirname(s.original_image_path))
    
    orig_url = f"/api/screening/file/{s.patient_id}/{parent_dir}/{orig_name}"
    proc_url = f"/api/screening/file/{s.patient_id}/{parent_dir}/{proc_name}"
    recs = json.loads(s.recommendations_json) if s.recommendations_json else {}
    stats = json.loads(s.color_stats_json) if s.color_stats_json else {}
    
    return {
        "id": s.id,
        "patient_id": s.patient_id,
        "patient_name": s.patient.full_name if s.patient else "Patient",
        "screening_type": s.screening_type,
        "estimated_hb": s.estimated_hb,
        "unit": s.unit,
        "confidence": s.confidence,
        "category": s.category,
        "is_anemic": s.is_anemic,
        "normal_min": s.normal_min,
        "normal_range_text": s.normal_range_text,
        "erythema_index": s.erythema_index,
        "quality_score": s.quality_score,
        "quality_status": s.quality_status,
        "color_stats": stats,
        "recommendations": recs,
        "original_image_url": orig_url,
        "processed_image_url": proc_url,
        "model_version": s.model_version,
        "validation_status": s.validation_status,
        "created_at": s.created_at.isoformat(),
        "disclaimer": "This is an AI-assisted screening estimate and not a confirmed medical diagnosis. Please consult a healthcare professional and confirm your hemoglobin level through appropriate laboratory testing."
    }

@router.get("/{screening_id}/pdf")
def download_pdf(screening_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Downloads clinical report PDF.
    """
    s = db.query(Screening).filter(Screening.id == screening_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Screening not found")
        
    if user.role != "doctor" and s.patient_id != user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    if not s.pdf_report_path or not os.path.exists(s.pdf_report_path):
        # Regenerate on demand
        pdf_path = os.path.join(os.path.dirname(s.original_image_path), f"report_{s.id}.pdf")
        patient_name = s.patient.full_name if s.patient else "Patient"
        age = s.patient.profile.age if s.patient and s.patient.profile else 25
        sex = s.patient.profile.sex if s.patient and s.patient.profile else "female"
        is_pregnant = s.patient.profile.is_pregnant if s.patient and s.patient.profile else False
        recs = json.loads(s.recommendations_json) if s.recommendations_json else {}
        
        pdf_meta = {
            "id": s.id,
            "patient_name": patient_name,
            "patient_age": age,
            "patient_sex": sex,
            "is_pregnant": is_pregnant,
            "screening_type": "Fingernail Bed Analysis" if s.screening_type == "nail" else "Palpebral Conjunctiva Analysis",
            "created_at": s.created_at.isoformat(),
            "estimated_hb": s.estimated_hb,
            "category": s.category,
            "confidence": s.confidence,
            "normal_range_text": s.normal_range_text,
            "quality_status": s.quality_status,
            "original_image_path": s.original_image_path,
            "processed_image_path": s.processed_image_path,
            "prevention": recs.get("prevention", "Maintain a balanced iron-rich diet."),
            "risks": recs.get("risks", "Untreated anemia risks chronic fatigue."),
            "advice": recs.get("advice", "Confirm with laboratory CBC testing."),
            "model_version": s.model_version,
            "validation_status": s.validation_status
        }
        generate_screening_pdf(pdf_meta, pdf_path)
        s.pdf_report_path = pdf_path
        db.commit()
        
    return FileResponse(s.pdf_report_path, media_type="application/pdf", filename=f"AnemiaWatch_Report_{s.id}.pdf")

@router.get("/file/{user_id}/{folder}/{filename}")
def serve_screening_image(user_id: int, folder: str, filename: str):
    """
    Safely serves patient inspection images.
    """
    safe_path = os.path.abspath(os.path.join(UPLOAD_ROOT, f"user_{user_id}", folder, filename))
    if not safe_path.startswith(UPLOAD_ROOT) or not os.path.exists(safe_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(safe_path)

@router.get("/articles")
def get_articles(db: Session = Depends(get_db)):
    """
    Returns English educational articles. Automatically migrates any Indonesian defaults.
    """
    # English article catalog (always enforced)
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

    # Detect Indonesian defaults and replace them
    indonesian_keywords = ["mengenal", "penyebab", "pencegahan", "makanan", "remaja", "dewasa", "faktor", "risikonya"]
    needs_migration = any(
        any(kw in a.title.lower() for kw in indonesian_keywords)
        for a in articles
    )

    if needs_migration or not articles:
        # Clear and re-seed with English articles
        db.query(Article).delete()
        for item in EN_ARTICLES:
            db.add(Article(**item))
        db.commit()
        articles = db.query(Article).all()
    elif len(articles) < len(EN_ARTICLES):
        # Add missing articles
        existing_titles = {a.title for a in articles}
        for item in EN_ARTICLES:
            if item["title"] not in existing_titles:
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
