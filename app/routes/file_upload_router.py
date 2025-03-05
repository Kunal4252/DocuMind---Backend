from fastapi import (
    APIRouter, 
    Depends, 
    File, 
    UploadFile, 
    HTTPException, 
    status
)

from app.dependencies import get_current_user
from app.services.file_validation_service import FileValidationService
from app.services.cloudinary_upload_service import CloudinaryUploadService

file_router = APIRouter(prefix="/files", tags=["file_upload"])

@file_router.post("/upload/document", response_model=dict)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    
    try:
        # Validate document file
        FileValidationService.validate_file(file, 'document')
        
        # Upload file to Cloudinary
        cloudinary_service = CloudinaryUploadService()
        file_url = cloudinary_service.upload_file(
            file, 
            'document', 
            current_user['user_id']
        )
        
        return {
            "message": "Document uploaded successfully",
            "file_url": file_url
        }
    
    except HTTPException as e:
        # Re-raise any HTTP exceptions from validation or upload
        raise e
    except Exception as e:
        # Handle any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )

@file_router.post("/upload/profile-image", response_model=dict)
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
   
    try:
        # Validate image file
        FileValidationService.validate_file(file, 'image')
        
        # Upload file to Cloudinary
        cloudinary_service = CloudinaryUploadService()
        file_url = cloudinary_service.upload_file(
            file, 
            'image', 
            current_user['user_id']
        )
        
        return {
            "message": "Profile image uploaded successfully",
            "file_url": file_url
        }
    
    except HTTPException as e:
        # Re-raise any HTTP exceptions from validation or upload
        raise e
    except Exception as e:
        # Handle any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )