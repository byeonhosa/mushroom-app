import os

# Ensure CI/pytest works even when .env isn't loaded
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test.db")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
# bcrypt at its production work factor would add a quarter of a second to
# every sign-in in the tests. The algorithm is the same at any factor.
os.environ.setdefault("PASSWORD_HASH_ROUNDS", "4")

import sys
from pathlib import Path

# Ensure `from app import ...` works when running pytest from backend/
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
