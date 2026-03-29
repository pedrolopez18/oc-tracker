# OC Tracker — Supply Chain

Sistema de seguimiento de órdenes de compra para entornos corporativos (oil & gas).

## Stack
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + pandas + Anthropic
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS

## Inicio rápido

### 1. Prerrequisitos
- Python 3.11+
- Node.js 18+
- PostgreSQL (o Docker)

### 2. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
copy .env.example .env         # completar con tus credenciales
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```

### 4. Con Docker (todo junto)
```bash
docker-compose up --build
```

## Uso
1. Abre http://localhost:3000
2. Arrastra el Excel maestro al área de upload
3. Explora las OCs en la tabla con filtros
4. Descarga plantillas por proveedor (ZIP)
5. Configura emails de proveedores y envía correos automáticos
