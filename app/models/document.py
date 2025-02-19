import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: f"DOC-{uuid.uuid4().hex[:8]}")  # Auto UUID
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    file_url = Column(String, nullable=False)  
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="documents")
