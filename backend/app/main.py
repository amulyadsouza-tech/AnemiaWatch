import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.app.database import engine, Base, SessionLocal
from backend.app.routers import auth, screening, doctor
from backend.app.services.ml_engine import (
    conj_regressor, conj_classifier, nail_regressor, conj_meta, nail_meta
)

# Initialize database tables
Base.metadata.create_all(bind=engine)

def _seed_test_users():
    """Create predefined test accounts on startup if they don't already exist."""
    from backend.app.models.schema import User, PatientProfile
    from backend.app.utils.security import hash_password

    db = SessionLocal()
    try:
        PREDEFINED = [
            {
                "email": "test@gmail.com",
                "password": "test1234",
                "full_name": "Test Patient",
                "role": "patient",
                "age": 24, "sex": "female", "is_pregnant": False, "blood_type": "O+"
            },
            {
                "email": "doctor@test.com",
                "password": "doctor1234",
                "full_name": "Dr. Test Doctor",
                "role": "doctor",
                "age": 35, "sex": "male", "is_pregnant": False, "blood_type": "A+"
            },
        ]
        for u_data in PREDEFINED:
            existing = db.query(User).filter(User.email == u_data["email"]).first()
            if not existing:
                user = User(
                    email=u_data["email"],
                    hashed_password=hash_password(u_data["password"]),
                    full_name=u_data["full_name"],
                    role=u_data["role"]
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                profile = PatientProfile(
                    user_id=user.id,
                    age=u_data["age"],
                    sex=u_data["sex"],
                    is_pregnant=u_data["is_pregnant"],
                    blood_type=u_data["blood_type"],
                    phone=""
                )
                db.add(profile)
                db.commit()
    finally:
        db.close()

_seed_test_users()

app = FastAPI(
    title="AnemiaWatch API",
    description="AI-Assisted Non-Invasive Anemia Screening Backend (HF26-35)",
    version="1.0.0"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(screening.router)
app.include_router(doctor.router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AnemiaWatch Screening Service",
        "version": "1.0.0",
        "models": {
            "conjunctiva_regressor_loaded": conj_regressor is not None,
            "conjunctiva_classifier_loaded": conj_classifier is not None,
            "nail_regressor_loaded": nail_regressor is not None,
            "conjunctiva_metrics": conj_meta,
            "nail_metrics": nail_meta
        },
        "database": "sqlite_connected"
    }

# Mount Frontend Build (SPA fallback)
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
ASSETS_DIR = os.path.join(DIST_DIR, "assets")

if os.path.exists(DIST_DIR):
    if os.path.exists(ASSETS_DIR):
        app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # API routes are handled by the routers above; only serve SPA for non-API paths
        if full_path.startswith("api/") or full_path.startswith("api"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = os.path.join(DIST_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
