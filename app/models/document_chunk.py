import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, default=lambda: f"CHUNK-{uuid.uuid4().hex[:8]}")
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    vector_db_id = Column(String, nullable=False)  # ID in vector database
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", backref="chunks") 