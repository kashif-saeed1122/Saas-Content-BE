from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from dependencies import get_current_user
import models
import schemas
from services import api_key_service

router = APIRouter(prefix="/api-keys", tags=["api-keys"])

@router.post("", response_model=schemas.APIKeyCreateResponse)
def create_api_key(
    request: schemas.APIKeyCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    api_key, key = api_key_service.create_api_key(db, current_user, request.name)
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": key,
        "prefix": api_key.prefix,
        "created_at": api_key.created_at
    }

@router.get("", response_model=List[schemas.APIKeyResponse])
def list_api_keys(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    api_keys = api_key_service.get_user_api_keys(db, current_user.id)
    return api_keys

@router.delete("/{key_id}")
def revoke_api_key(
    key_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    api_key = db.query(models.APIKey).filter(
        models.APIKey.id == key_id,
        models.APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key_service.revoke_api_key(db, api_key)
    return {"success": True, "message": "API key revoked"}