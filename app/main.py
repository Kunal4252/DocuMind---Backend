from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time

from app.utils.firebase import initialize_firebase
from app.db.init_db import init_db, close_db_connection
from app.routes.user_routes import user_router
from app.routes.document_routes import document_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Allow requests from this origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    print(f"Request to {request.url.path} took {process_time:.4f} seconds")
    return response

@app.on_event("startup")
def startup():
    initialize_firebase()  
    init_db()  
    
@app.on_event("shutdown")
def shutdown():
    close_db_connection()

app.include_router(user_router)
app.include_router(document_router)