from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.dialects.postgresql import JSONB
from core.db.connection import Base


class IoTEvent(Base):
    __tablename__ = "iot_events"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    device_id  = Column(String(255), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload    = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
