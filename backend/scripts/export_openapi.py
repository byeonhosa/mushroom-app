import json
import os
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///./contract-export.db")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from app.main import app  # noqa: E402


json.dump(app.openapi(), sys.stdout, indent=2)
sys.stdout.write("\n")
