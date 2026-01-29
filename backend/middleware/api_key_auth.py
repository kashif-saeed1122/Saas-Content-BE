from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from services import api_key_service
from models import User

async def validate_api_key_header(
    x_api_key: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    user = api_key_service.validate_api_key(db, x_api_key)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return user
