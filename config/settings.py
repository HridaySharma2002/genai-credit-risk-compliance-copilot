"""
config/settings.py
------------------
Centralized configuration management for the GenAI Credit Risk & Compliance Copilot.
Loads configuration from .env and environment variables.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from the project root
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "credit_risk.db"))

# Google Gemini API Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

# Data File Paths
DEFAULT_CSV_PATH = str(BASE_DIR / "transactions.csv")
DATA_DIR = BASE_DIR / "data"
