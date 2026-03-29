from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.excel_service import parse_excel, split_by_supplier
from app.services.email_service import send_supplier_email
from app.services.ai_service import generate_email_body
from app.services.supplier_service import get_email_map
from app.models.email_log import EmailLog

router = APIRouter()


@router.post("/send-all")
async def send_all(
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db),
):
    """
    Envía un Excel personalizado a cada proveedor (empresa externa).
    Requiere que los emails estén configurados en la tabla Supplier.
    """
    content   = await file.read()
    df, batch = parse_excel(content)
    files     = split_by_supplier(df)     # agrupa por "Proveedor"
    email_map = get_email_map(db)
    results   = []

    for proveedor, excel_bytes in files.items():
        email_to = email_map.get(proveedor, "")
        if not email_to:
            results.append({"supplier": proveedor, "status": "sin_email"})
            continue

        # Filas del proveedor para el cuerpo del email
        orders_data = df[df["Proveedor"] == proveedor].to_dict("records")
        body        = generate_email_body(proveedor, orders_data)
        filename    = f"OC_{proveedor.replace(' ', '_')}.xlsx"

        result = send_supplier_email(
            supplier    = proveedor,
            email_to    = email_to,
            excel_bytes = excel_bytes,
            body        = body,
            filename    = filename,
        )
        result["supplier"] = proveedor

        log_entry = EmailLog(
            batch_id  = batch,
            supplier  = proveedor,
            email_to  = email_to,
            status    = result["status"],
            error_msg = result.get("reason", ""),
        )
        db.add(log_entry)
        results.append(result)

    db.commit()
    sent     = sum(1 for r in results if r["status"] == "sent")
    errors   = sum(1 for r in results if r["status"] == "error")
    no_email = len(results) - sent - errors

    return {
        "sent":     sent,
        "errors":   errors,
        "no_email": no_email,
        "detail":   results,
    }
