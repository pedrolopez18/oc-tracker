"""
Script de diagnóstico SMTP.
Ejecutar desde la carpeta backend/:
    python test_smtp.py
"""
import smtplib
import sys
from dotenv import load_dotenv
import os

load_dotenv()   # lee backend/.env

HOST     = os.getenv("SMTP_HOST",     "smtp.gmail.com")
PORT     = int(os.getenv("SMTP_PORT", "587"))
USER     = os.getenv("SMTP_USER",     "")
PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM     = os.getenv("SMTP_FROM",     USER)

print(f"HOST     : {HOST}:{PORT}")
print(f"USER     : {USER}")
print(f"PASSWORD : {'*' * len(PASSWORD)} ({len(PASSWORD)} chars)")
print(f"FROM     : {FROM}")
print()

if not USER or not PASSWORD:
    print("❌ SMTP_USER o SMTP_PASSWORD vacíos. Revisa backend/.env")
    sys.exit(1)

try:
    print("Conectando al servidor SMTP…")
    with smtplib.SMTP(HOST, PORT, timeout=10) as s:
        s.ehlo()
        s.starttls()
        s.ehlo()
        print("STARTTLS OK")
        s.login(USER, PASSWORD)
        print(f"✅ Login OK — credenciales válidas para {USER}")
except smtplib.SMTPAuthenticationError as e:
    print(f"❌ Autenticación fallida: {e}")
    print("   → Verifica que la contraseña sea una App Password de Google")
    print("   → Google → Cuenta → Seguridad → Contraseñas de aplicaciones")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    sys.exit(1)
