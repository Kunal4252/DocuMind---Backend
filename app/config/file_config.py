# Allowed MIME types for documents
ALLOWED_DOCUMENT_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
}

# Allowed MIME types for images (profile pictures)
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg",
}

# File size limits (in bytes)
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 5MB for documents
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB for profile images