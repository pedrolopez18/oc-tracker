import os
from functools import lru_cache
from pathlib import Path

# Cargar .env desde el directorio backend (si existe)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # python-dotenv no instalado; se usan variables de entorno del sistema


class Settings:
    database_url:      str = os.getenv("DATABASE_URL",      "sqlite:///./test.db")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    smtp_host:         str = os.getenv("SMTP_HOST",         "smtp.gmail.com")
    smtp_port:         int = int(os.getenv("SMTP_PORT",     "587"))
    smtp_user:         str = os.getenv("SMTP_USER",         "")
    smtp_password:     str = os.getenv("SMTP_PASSWORD",     "")
    smtp_from:         str = os.getenv("SMTP_FROM",         "")
    upload_dir:        str = os.getenv("UPLOAD_DIR",        "uploads")
    output_dir:        str = os.getenv("OUTPUT_DIR",        "outputs")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
