from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.dependencies import get_current_user
from app.services.user_service import UserService
from app.schemas.user import EmailSignInData, UserProfileResponse, UserProfileUpdate

user_router = APIRouter(prefix="/users", tags=["users"])
user_service = UserService()

@user_router.post("/auth/signup", response_model=dict, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: EmailSignInData = Body(...),
    db: Session = Depends(get_db),
    decoded_token: dict = Depends(get_current_user)
):
    """
    Register a new user in PostgreSQL after Firebase authentication.
    """
    try:
        firebase_uid = decoded_token["uid"]
        user = user_service.create_user(db, firebase_uid, user_data)
        return {"uid": user.id, "message": "User created successfully"}
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@user_router.post("/auth/google-signup", response_model=dict, status_code=status.HTTP_201_CREATED)
async def google_signup(
    db: Session = Depends(get_db),
    decoded_token: dict = Depends(get_current_user)
):
    """
    Register or fetch a Google sign-in user in PostgreSQL.
    """
    try:
        firebase_uid = decoded_token["uid"]
        email = decoded_token.get("email")
        name = decoded_token.get("name") or (email.split("@")[0] if email else "Unknown")
        user = user_service.get_or_create_user(db, firebase_uid, email, name)
        return {"uid": user.id, "message": "User fetched/created successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@user_router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    db: Session = Depends(get_db),
    decoded_token: dict = Depends(get_current_user)
):
    """
    Fetch user profile details.
    """
    try:
        firebase_uid = decoded_token["uid"]
        user = user_service.get_user_by_id(db, firebase_uid)
        return user
    except HTTPException as e:
        raise e  # Re-raise HTTPException (e.g., user not found)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )

@user_router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    profile_data: UserProfileUpdate = Body(...),
    db: Session = Depends(get_db),
    decoded_token: dict = Depends(get_current_user)
):
    """
    Update user profile.
    """
    try:
        firebase_uid = decoded_token["uid"]
        updated_user = user_service.update_user_profile(db, firebase_uid, profile_data)
        return updated_user
    except HTTPException as e:
        raise e  # Re-raise HTTPException (e.g., user not found)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )