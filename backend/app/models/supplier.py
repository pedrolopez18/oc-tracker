from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class Supplier(Base):
    __tablename__ = "suppliers"

    id       = Column(Integer, primary_key=True)
    name     = Column(String(150), unique=True, index=True)
    email    = Column(String(200))
    active   = Column(Boolean, default=True)
