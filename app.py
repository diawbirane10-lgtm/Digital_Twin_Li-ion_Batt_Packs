"""
Entrypoint Streamlit Cloud — redirige vers visualization/dashboard/app.py
Ne pas modifier ce fichier.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

exec(
    open(ROOT / "visualization" / "dashboard" / "app.py", encoding="utf-8").read()
)
