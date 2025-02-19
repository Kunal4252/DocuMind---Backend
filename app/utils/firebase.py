import os
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, status
from dotenv import load_dotenv

load_dotenv()


def initialize_firebase():
    
    SERVICE_ACCOUNT_KEY_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)


def verify_token(id_token: str):
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )