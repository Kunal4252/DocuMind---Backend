from fastapi import FastAPI
from app.utils.firebase import initialize_firebase
from app.routes import profile

app = FastAPI()

# Initialize Firebase Admin SDK
initialize_firebase()

# Include the profile route
app.include_router(profile.router, prefix="/api", tags=["profile"])