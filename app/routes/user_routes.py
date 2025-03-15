from fastapi import APIRouter, Depends, Body, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db.session import get_db
from app.dependencies import get_current_user
from app.services.user_service import UserService
from app.schemas.user import EmailSignInData, UserProfileResponse, UserProfileUpdate
from app.services.file_validation_service import FileValidationService
from app.services.cloudinary_upload_service import CloudinaryUploadService
from app.models.user import User

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

@user_router.post("/profile/upload-image", response_model=dict)
async def upload_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Upload a profile image for the current user"""
    try:
        user_id = current_user["uid"]
        
        # Validate image file
        FileValidationService.validate_file(file, 'image')
        
        # Upload file to Cloudinary
        cloudinary_service = CloudinaryUploadService()
        file_url = cloudinary_service.upload_file(
            file, 
            'image', 
            user_id
        )
        
        # Update the user's profile_image field in the database
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.profile_image = file_url
            db.commit()
        
        return {
            "message": "Profile image uploaded successfully",
            "file_url": file_url
        }
    
    except HTTPException as e:
        # Re-raise any HTTP exceptions from validation or upload
        raise e
    except Exception as e:
        # Handle any unexpected errors
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )