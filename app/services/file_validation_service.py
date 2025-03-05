import os
import magic
from typing import Union
from fastapi import UploadFile, HTTPException, status
from datetime import datetime

from app.config.file_config import (
    ALLOWED_DOCUMENT_MIME_TYPES, 
    ALLOWED_IMAGE_MIME_TYPES, 
    MAX_DOCUMENT_SIZE, 
    MAX_IMAGE_SIZE
)

class FileValidationService:
    @staticmethod
    def validate_file_type(file: UploadFile, file_type: str) -> None:
        
        allowed_mime_types = (
            ALLOWED_DOCUMENT_MIME_TYPES if file_type == 'document'
            else ALLOWED_IMAGE_MIME_TYPES
        )
        
        
        try:
           
            file_content = file.file.read(2048)
            file.file.seek(0)  
            
            
            mime = magic.from_buffer(file_content, mime=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error detecting file type: {str(e)}"
            )
        
        
        if mime not in allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Detected type: {mime}. Allowed types: {', '.join(allowed_mime_types)}"
            )
    
    @staticmethod
    def validate_file_size(file: UploadFile, file_type: str) -> None:
        
        max_size = (
            MAX_DOCUMENT_SIZE if file_type == 'document'
            else MAX_IMAGE_SIZE
        )
        
        # Check file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)  # Reset file pointer
        
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum limit of {max_size_mb}MB"
            )
    
    @staticmethod
    def validate_file(file: UploadFile, file_type: str) -> None:
        
        # Validate file type using magic
        FileValidationService.validate_file_type(file, file_type)
        
        # Validate file size
        FileValidationService.validate_file_size(file, file_type)

