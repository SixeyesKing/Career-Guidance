import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")


def setting(name, default=""):
    return os.getenv(name, default).strip()


DATABASE_PATH = Path(setting("DATABASE_PATH", "data/career_guidance.db"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = ROOT / DATABASE_PATH

CHROMA_PATH = Path(setting("CHROMA_PATH", "data/chroma"))
if not CHROMA_PATH.is_absolute():
    CHROMA_PATH = ROOT / CHROMA_PATH

EXPORTS_PATH = ROOT / "exports"
KNOWLEDGE_PATH = ROOT / "data" / "knowledge"
