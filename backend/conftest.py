import sys
from pathlib import Path

# Ensure `from app import ...` works when running pytest from backend/
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
