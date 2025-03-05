import os
from datetime import datetime
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status

from app.config.cloudinary_config import (
    CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY,
    CLOUDINARY_API_SECRET,
    CLOUDINARY_DOCUMENT_FOLDER,
    CLOUDINARY_PROFILE_IMAGE_FOLDER
)

class CloudinaryUploadService:
    def __init__(self):
        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET
        )
    
    def generate_custom_file_name(self, user_id: str, original_file_name: str) -> str:
        file_extension = os.path.splitext(original_file_name)[1]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{user_id}_{timestamp}{file_extension}"
    
    def upload_file(self, file: UploadFile, file_type: str, user_id: str) -> str:
        try:
            folder = (
                CLOUDINARY_DOCUMENT_FOLDER if file_type == 'document'
                else CLOUDINARY_PROFILE_IMAGE_FOLDER
            )
            custom_file_name = self.generate_custom_file_name(user_id, file.filename)
            public_id = f"{folder}/{custom_file_name}"
            upload_result = cloudinary.uploader.upload(
                file.file,
                folder=folder,
                public_id=public_id,
                resource_type='auto'
            )
            return upload_result['secure_url']
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"File upload failed: {str(e)}"
            )
