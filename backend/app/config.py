"""Runtime settings, overridable with environment variables (see .env.example)."""
import os

MAX_CHARS = int(os.getenv("MAX_CHARS", "300000"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "history.db"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",") if o.strip()]
CACHE_SIZE = int(os.getenv("CACHE_SIZE", "64"))
