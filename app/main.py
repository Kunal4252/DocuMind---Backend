from fastapi import FastAPI
from app.utils.firebase import initialize_firebase
from app.routes.user_routes import user_router
from app.db.init_db import init_db
from app.routes.file_upload_router import file_router
app = FastAPI()

@app.on_event("startup")
def startup():
    initialize_firebase()  
    init_db()  
    

app.include_router(user_router)
app.include_router(file_router)