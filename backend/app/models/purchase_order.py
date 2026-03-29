from sqlalchemy import Column, Integer, String, Date, Numeric, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id            = Column(Integer, primary_key=True, index=True)
    batch_id      = Column(String(36), index=True)
    oc            = Column(String(20))
    pos           = Column(String(10))
    oc_pos        = Column(String(35), index=True)
    fecha_doc     = Column(Date, nullable=True)
    centro        = Column(String(20))
    material      = Column(String(50))
    descripcion   = Column(Text)
    ump           = Column(String(10))
    cant_pedido   = Column(Numeric, nullable=True)
    por_entregar  = Column(Numeric, nullable=True)
    proveedor     = Column(String(200), index=True)   # empresa externa (correcto)
    comprador_oc  = Column(String(150), index=True)   # persona interna
    fe_segun_oc   = Column(Date, nullable=True)
    ultima_fe     = Column(Date, nullable=True)
    prioridad     = Column(String(20))
    comentarios   = Column(Text)
    estado        = Column(String(50))
    motivo_estado = Column(Text)
    dias_retraso  = Column(Integer, default=0)
    ai_summary    = Column(Text)
    ai_risk       = Column(String(20))   # En plazo / En riesgo / Crítico
    uploaded_at   = Column(DateTime(timezone=True), server_default=func.now())
