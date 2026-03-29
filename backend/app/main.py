import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
log = logging.getLogger(__name__)

app = FastAPI(
    title="OC Tracker API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # Orígenes locales explícitos
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    # Vercel genera URLs del tipo https://proyecto-xxx.vercel.app
    # allow_origins no soporta wildcards de subdominio — se usa regex
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers principales (file-based, sin base de datos) ───────────────────────
from app.routers import upload, chat, report
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(chat.router,   prefix="/api/chat",   tags=["chat"])
app.include_router(report.router, prefix="/api/report", tags=["report"])

# ── Routers secundarios (requieren SQLAlchemy — carga condicional) ─────────────
try:
    from app.routers import orders, suppliers, email, ai
    from app.database import create_tables
    create_tables()
    app.include_router(orders.router,    prefix="/api/orders",    tags=["orders"])
    app.include_router(suppliers.router, prefix="/api/suppliers", tags=["suppliers"])
    app.include_router(email.router,     prefix="/api/email",     tags=["email"])
    app.include_router(ai.router,        prefix="/api/ai",        tags=["ai"])
    log.info("Routers de base de datos cargados correctamente.")
except Exception as e:
    log.warning("Routers de base de datos no disponibles: %s", e)
    log.warning("El sistema funciona en modo file-only (upload + chat).")


@app.get("/ping")
def ping():
    return {"status": "ok", "version": "1.0.0"}
