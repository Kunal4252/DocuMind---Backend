from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class EmailSignInData(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: str  # Firebase UID
    email: EmailStr
    name: str
    profile_image: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    

    class Config:
        from_attributes = True  


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    profile_image: Optional[str] = None  
    phone: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None