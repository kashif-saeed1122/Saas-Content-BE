from sqlalchemy.orm import Session
from models import APIKey, User
import secrets
import hashlib
from datetime import datetime
import uuid

def generate_api_key() -> tuple[str, str, str]:
    key = f"sk_{secrets.token_urlsafe(32)}"
    prefix = key[:12]
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key, prefix, key_hash

def create_api_key(db: Session, user: User, name: str = None) -> tuple[APIKey, str]:
    key, prefix, key_hash = generate_api_key()
    
    api_key = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        prefix=prefix,
        name=name
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return api_key, key

def get_user_api_keys(db: Session, user_id: uuid.UUID):
    return db.query(APIKey).filter(
        APIKey.user_id == user_id,
        APIKey.revoked_at.is_(None)
    ).order_by(APIKey.created_at.desc()).all()

def validate_api_key(db: Session, key: str) -> User:
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    
    api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.revoked_at.is_(None)
    ).first()
    
    if not api_key:
        return None
    
    api_key.last_used_at = datetime.utcnow()
    db.commit()
    
    return api_key.user

def revoke_api_key(db: Session, api_key: APIKey):
    api_key.revoked_at = datetime.utcnow()
    db.commit()
    return api_key