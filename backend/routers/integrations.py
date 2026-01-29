from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime

from database import get_db
from dependencies import get_current_user
import models
import schemas
from services import posting_service

router = APIRouter(prefix="/integrations", tags=["integrations"])

@router.post("", response_model=schemas.WebhookIntegrationResponse)
def create_integration(
    request: schemas.WebhookIntegrationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integration = models.WebhookIntegration(
        user_id=current_user.id,
        name=request.name,
        webhook_url=request.webhook_url,
        webhook_secret=request.webhook_secret,
        platform_type=request.platform_type
    )
    
    db.add(integration)
    db.commit()
    db.refresh(integration)
    
    return integration

@router.get("", response_model=List[schemas.WebhookIntegrationResponse])
def list_integrations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integrations = db.query(models.WebhookIntegration).filter(
        models.WebhookIntegration.user_id == current_user.id
    ).all()
    return integrations

@router.patch("/{integration_id}", response_model=schemas.WebhookIntegrationResponse)
def update_integration(
    integration_id: uuid.UUID,
    request: schemas.WebhookIntegrationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.WebhookIntegration).filter(
        models.WebhookIntegration.id == integration_id,
        models.WebhookIntegration.user_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    integration.name = request.name
    integration.webhook_url = request.webhook_url
    integration.webhook_secret = request.webhook_secret
    integration.platform_type = request.platform_type
    integration.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(integration)
    
    return integration

@router.delete("/{integration_id}")
def delete_integration(
    integration_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    integration = db.query(models.WebhookIntegration).filter(
        models.WebhookIntegration.id == integration_id,
        models.WebhookIntegration.user_id == current_user.id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    db.delete(integration)
    db.commit()
    
    return {"success": True, "message": "Integration deleted"}

@router.post("/test")
def test_webhook(
    request: schemas.WebhookTestRequest,
    current_user: models.User = Depends(get_current_user)
):
    success, message = posting_service.test_webhook_connection(
        request.webhook_url,
        request.webhook_secret
    )
    
    return {
        "success": success,
        "message": message
    }