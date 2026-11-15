import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

if IS_SERVERLESS:
    DATABASE_DIR = "/tmp"
else:
    DATABASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    try:
        os.makedirs(DATABASE_DIR, exist_ok=True)
    except OSError:
        DATABASE_DIR = "/tmp"

DATABASE_URL = f"sqlite:///{os.path.join(DATABASE_DIR, 'anemiawatch.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
