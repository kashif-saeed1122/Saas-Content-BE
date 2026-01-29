from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from dependencies import get_current_user
import models
import schemas
from services import credit_service

router = APIRouter(prefix="/credits", tags=["credits"])

@router.get("", response_model=schemas.CreditBalanceResponse)
def get_credit_balance(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {
        "credits": current_user.credits,
        "plan": current_user.plan
    }

@router.get("/transactions", response_model=List[schemas.CreditTransactionResponse])
def get_transactions(
    limit: int = 50,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    transactions = credit_service.get_user_transactions(db, current_user.id, limit)
    return transactions

@router.post("/purchase")
def purchase_credits(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {
        "message": "Stripe integration coming soon",
        "current_credits": current_user.credits
    }