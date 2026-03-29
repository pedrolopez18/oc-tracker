from sqlalchemy.orm import Session
from app.models.supplier import Supplier

def get_all(db: Session) -> list[Supplier]:
    return db.query(Supplier).filter(Supplier.active == True).all()

def upsert(db: Session, name: str, email: str = "") -> Supplier:
    s = db.query(Supplier).filter(Supplier.name == name).first()
    if not s:
        s = Supplier(name=name, email=email)
        db.add(s)
    elif email:
        s.email = email
    db.commit()
    db.refresh(s)
    return s

def get_email_map(db: Session) -> dict[str, str]:
    suppliers = db.query(Supplier).filter(
        Supplier.active == True,
        Supplier.email != None,
        Supplier.email != ""
    ).all()
    return {s.name: s.email for s in suppliers}
