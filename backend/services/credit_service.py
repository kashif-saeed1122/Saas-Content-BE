from sqlalchemy.orm import Session
from models import User, CreditTransaction
import uuid

TOKENS_PER_CREDIT = 2000

def calculate_credits_from_tokens(tokens: int) -> int:
    return max(1, (tokens + TOKENS_PER_CREDIT - 1) // TOKENS_PER_CREDIT)

def check_and_deduct_credits(db: Session, user: User, estimated_tokens: int = None) -> bool:
    credits_needed = calculate_credits_from_tokens(estimated_tokens) if estimated_tokens else 1
    
    if user.credits < credits_needed:
        return False
    
    user.credits -= credits_needed
    db.commit()
    return True

def deduct_credits_for_tokens(
    db: Session,
    user: User,
    tokens_used: int,
    reference_type: str,
    reference_id: uuid.UUID,
    description: str = None
):
    credits_to_deduct = calculate_credits_from_tokens(tokens_used)
    
    user.credits -= credits_to_deduct
    
    transaction = CreditTransaction(
        user_id=user.id,
        amount=-credits_to_deduct,
        balance_after=user.credits,
        type='usage',
        reference_type=reference_type,
        reference_id=reference_id,
        description=description or f"Used {tokens_used} tokens",
        tokens_consumed=tokens_used
    )
    
    db.add(transaction)
    db.commit()
    
    return credits_to_deduct

def add_credits(
    db: Session,
    user: User,
    amount: int,
    type: str = 'purchase',
    description: str = None
):
    user.credits += amount
    
    transaction = CreditTransaction(
        user_id=user.id,
        amount=amount,
        balance_after=user.credits,
        type=type,
        description=description or f"Added {amount} credits"
    )
    
    db.add(transaction)
    db.commit()
    
    return transaction

def get_user_transactions(db: Session, user_id: uuid.UUID, limit: int = 50):
    return db.query(CreditTransaction).filter(
        CreditTransaction.user_id == user_id
    ).order_by(CreditTransaction.created_at.desc()).limit(limit).all()
