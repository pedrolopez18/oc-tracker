from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.purchase_order import PurchaseOrder
from app.services.ai_service import detect_risks, summarize_comments

router = APIRouter()


@router.get("/risks")
def risk_analysis(db: Session = Depends(get_db)):
    orders = db.query(PurchaseOrder).all()
    if not orders:
        return {"critical_suppliers": [], "recommended_actions": []}

    data = [
        {
            "oc_pos":       o.oc_pos,
            "proveedor":    o.proveedor,      # empresa externa (correcto)
            "comprador_oc": o.comprador_oc,   # persona interna
            "dias_retraso": o.dias_retraso,
            "estado":       o.estado,
        }
        for o in orders
    ]
    return detect_risks(data)


@router.post("/summarize/{oc_pos}")
def summarize_order(oc_pos: str, db: Session = Depends(get_db)):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.oc_pos == oc_pos).first()
    if not o:
        return {"error": "OC no encontrada"}
    summary    = summarize_comments(o.comentarios or "")
    o.ai_summary = summary
    db.commit()
    return {"oc_pos": oc_pos, "summary": summary}
