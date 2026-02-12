import requests
import hmac
import hashlib
import json
from models import Article, User

def generate_webhook_signature(payload: dict, secret: str) -> str:
    payload_str = json.dumps(payload, sort_keys=True)
    return hmac.new(
        secret.encode('utf-8'),
        payload_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def post_article_to_webhook(
    article: Article,
    user: User,
    webhook_url: str,
    webhook_secret: str = None,
    timeout: int = 30
) -> tuple[bool, str]:
    
    payload = {
        "article_id": str(article.id),
        "campaign_id": str(article.campaign_id) if article.campaign_id else None,
        "title": article.topic or article.raw_query,
        "content": article.content,
        "category": article.category,
        "scheduled_at": article.scheduled_at.isoformat() if article.scheduled_at else None,
        "created_at": article.created_at.isoformat()
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "NeuralGen-Webhook/1.0"
    }
    
    if webhook_secret:
        headers["X-Webhook-Signature"] = generate_webhook_signature(payload, webhook_secret)
    
    api_key = user.api_keys[0] if user.api_keys else None
    if api_key:
        headers["X-API-Key"] = api_key.prefix
    
    try:
        response = requests.post(webhook_url, json=payload, headers=headers, timeout=timeout)
        return (True, "Success") if response.status_code == 200 else (False, f"HTTP {response.status_code}")
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)[:200]

def test_webhook_connection(webhook_url: str, webhook_secret: str = None) -> tuple[bool, str]:
    from datetime import datetime
    test_payload = {"test": True, "timestamp": datetime.utcnow().isoformat()}
    headers = {"Content-Type": "application/json"}
    
    if webhook_secret:
        headers["X-Webhook-Signature"] = generate_webhook_signature(test_payload, webhook_secret)
    
    try:
        response = requests.post(webhook_url, json=test_payload, headers=headers, timeout=10)
        return (True, "Success") if response.status_code == 200 else (False, f"HTTP {response.status_code}")
    except Exception as e:
        return False, str(e)[:200]