from app.db.session import engine, Base
from app.models.user import User
from app.models.document import Document
from app.models.chat_history import ChatHistory

def init_db():
    print("creating tables")
    Base.metadata.create_all(bind=engine)
    print("created tables successfully")
    