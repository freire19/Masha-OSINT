# src/config/masha_config.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CNPJ_DB_PATH = DATA_DIR / "cnpj.db"

# Por padrão, NÃO usa banco (modo OSINT puro).
USE_LOCAL_CNPJ_DB = os.getenv("MASHA_USE_LOCAL_CNPJ_DB", "false").lower() == "true"

HAS_LOCAL_CNPJ = USE_LOCAL_CNPJ_DB and CNPJ_DB_PATH.exists()
