from  sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,              # Adjust based on expected load
    max_overflow=20,           # Additional connections when pool is full
    pool_timeout=30,           # Seconds to wait for a connection from pool
    pool_recycle=1800          # Recycle connections after 30 minutes
)

SessionLocal = sessionmaker(autocommit = False,autoflush=False,bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

        