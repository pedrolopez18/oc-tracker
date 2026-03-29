from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.database import Base

class EmailLog(Base):
    __tablename__ = "email_logs"

    id        = Column(Integer, primary_key=True)
    batch_id  = Column(String(36))
    supplier  = Column(String(150))
    email_to  = Column(String(200))
    status    = Column(String(20))   # sent / error
    error_msg = Column(Text)
    sent_at   = Column(DateTime(timezone=True), server_default=func.now())
