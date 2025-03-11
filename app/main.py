from fastapi import FastAPI
from app.utils.firebase import initialize_firebase
from app.routes.user_routes import user_router
from app.db.init_db import init_db, close_db_connection
from app.routes.file_upload_router import file_router
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Allow requests from this origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)
@app.on_event("startup")
def startup():
    initialize_firebase()  
    init_db()  
    
@app.on_event("shutdown")
def shutdown():
    close_db_connection()

app.include_router(user_router)
app.include_router(file_router)