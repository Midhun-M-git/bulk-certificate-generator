import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    PROJECT_NAME: str = "Bulk Certificate Generator API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Database (SQLite by default, easily swapped for PostgreSQL via env var)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{BASE_DIR / 'certificate_generator.db'}"
    )
    
    # Storage
    STORAGE_DIR: Path = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage" / "certificates")))
    
    # Batch processing limits
    MAX_RECIPIENTS_PER_BATCH: int = int(os.getenv("MAX_RECIPIENTS_PER_BATCH", "5000"))
    
    # Base URL
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

settings = Settings()
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
