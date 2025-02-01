
from fastapi import APIRouter, Depends
from app.dependencies import get_current_user

router = APIRouter()

@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    
    return {
        "message": "User profile retrieved successfully",
        "user": {
            "uid": user["uid"],
            "email": user.get("email", ""),
            "name": user.get("name", ""),
        },
    }