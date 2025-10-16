# config.py
from dotenv import load_dotenv
from datetime import timedelta
import os

# Carga las variables del archivo .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-secreta-desarrollo-123")
    ORACLE_USER = os.getenv("ORA_USER", "SYSTEM")
    ORACLE_PASSWORD = os.getenv("ORA_PASS", "12345678")
    ORACLE_DSN = os.getenv("ORA_DSN", "localhost:1521/XE")
    
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
