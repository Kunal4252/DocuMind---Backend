import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from a .env file

# Cloudinary API Credentials
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

# Define Folders for Different Upload Types
CLOUDINARY_DOCUMENT_FOLDER = "documents"  # Folder for storing documents
CLOUDINARY_PROFILE_IMAGE_FOLDER = "profile_images"  # Folder for storing profile pictures
