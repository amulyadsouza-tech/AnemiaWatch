import os
from typing import List

class Settings:
    PROJECT_NAME: str = "AnemiaWatch"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")
    
    # Database
    RAW_DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    
    @property
    def DATABASE_URL(self) -> str:
        if not self.RAW_DATABASE_URL:
            # Local fallback SQLite
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
            os.makedirs(base_dir, exist_ok=True)
            return f"sqlite:///{os.path.join(base_dir, 'anemiawatch.db')}"
        
        url = self.RAW_DATABASE_URL.strip()
        # Render / Heroku compatibility: convert postgres:// or postgresql:// to postgresql+psycopg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    # Security & Tokens
    JWT_SECRET: str = os.environ.get("JWT_SECRET", os.environ.get("ANEMIAWATCH_SECRET_KEY", "anemiawatch-production-medical-key-2026-argon2id"))
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "14"))
    
    # Rate Limiting & Account Security
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    
    # CORS
    FRONTEND_URL: str = os.environ.get("FRONTEND_URL", "https://anemiawatch.vercel.app")
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        raw = os.environ.get("ALLOWED_ORIGINS", "*")
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        if not origins or "*" in origins:
            return ["*"]
        return origins

settings = Settings()
