from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.purchase_order import PurchaseOrder

router = APIRouter()


@router.get("/")
def list_orders(
    db:            Session = Depends(get_db),
    supplier:      str     = Query(""),
    priority:      str     = Query(""),
    risk:          str     = Query(""),
    search:        str     = Query(""),
    only_critical: bool    = Query(False),
    skip:          int     = Query(0),
    limit:         int     = Query(500),
):
    q = db.query(PurchaseOrder)
    if supplier:
        q = q.filter(PurchaseOrder.proveedor == supplier)
    if priority:
        q = q.filter(PurchaseOrder.prioridad == priority)
    if risk:
        q = q.filter(PurchaseOrder.ai_risk == risk)
    if only_critical:
        q = q.filter(PurchaseOrder.dias_retraso > 15)
    if search:
        term = f"%{search}%"
        q = q.filter(
            PurchaseOrder.oc_pos.ilike(term) |
            PurchaseOrder.descripcion.ilike(term) |
            PurchaseOrder.material.ilike(term) |
            PurchaseOrder.proveedor.ilike(term)
        )
    orders = q.order_by(PurchaseOrder.dias_retraso.desc()).offset(skip).limit(limit).all()
    return [_serialize(o) for o in orders]


@router.get("/{oc_pos}")
def get_order(oc_pos: str, db: Session = Depends(get_db)):
    o = db.query(PurchaseOrder).filter(
        PurchaseOrder.oc_pos == oc_pos
    ).first()
    if not o:
        return {"error": "OC no encontrada"}
    return _serialize(o)


def _serialize(o: PurchaseOrder) -> dict:
    return {
        "id":            o.id,
        "oc_pos":        o.oc_pos,
        "proveedor":     o.proveedor,      # empresa externa
        "comprador_oc":  o.comprador_oc,   # persona interna
        "descripcion":   o.descripcion,
        "material":      o.material,
        "fe_segun_oc":   str(o.fe_segun_oc) if o.fe_segun_oc else None,
        "ultima_fe":     str(o.ultima_fe) if o.ultima_fe else None,
        "prioridad":     o.prioridad,
        "estado":        o.estado,
        "dias_retraso":  o.dias_retraso,
        "ai_risk":       o.ai_risk,
        "ai_summary":    o.ai_summary,
        "comentarios":   o.comentarios,
        "motivo_estado": o.motivo_estado,
    }
