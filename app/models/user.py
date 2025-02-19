from sqlalchemy import Column, String, DateTime, Boolean
from datetime import datetime
from app.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True) 
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    profile_image = Column(String, nullable=True)  
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)  
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    

    