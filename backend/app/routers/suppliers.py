from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.supplier_service import get_all, upsert, get_email_map
from app.services.excel_service import parse_excel, split_by_supplier
from app.models.purchase_order import PurchaseOrder
import io, zipfile

router = APIRouter()

@router.get("/")
def list_suppliers(db: Session = Depends(get_db)):
    return [{"name": s.name, "email": s.email} for s in get_all(db)]

@router.put("/{name}/email")
def update_email(name: str, email: str, db: Session = Depends(get_db)):
    s = upsert(db, name, email)
    return {"name": s.name, "email": s.email}

@router.post("/generate-zip")
async def generate_zip(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Recibe el Excel maestro, genera un ZIP con un Excel por proveedor.
    Cada Excel mantiene exactamente los mismos encabezados originales.
    """
    content = await file.read()
    df, _ = parse_excel(content)
    supplier_files = split_by_supplier(df)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for supplier, excel_bytes in supplier_files.items():
            safe_name = supplier.replace("/", "-").replace("\\", "-")
            zf.writestr(f"OC_{safe_name}.xlsx", excel_bytes)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=OC_por_proveedor.zip"}
    )
