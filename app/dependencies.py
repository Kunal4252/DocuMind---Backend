from fastapi import Depends, HTTPException, status, Header
from app.utils.firebase import verify_token

async def get_current_user(authorization: str = Header(None)):
    
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
   
    id_token = authorization.split("Bearer ")[1]
    
    
    decoded_token = verify_token(id_token)
    return decoded_token