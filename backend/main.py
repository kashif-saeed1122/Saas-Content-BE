from fastapi import FastAPI, Depends, HTTPException, status, Response, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
import uuid
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Imports from your files
import models, schemas
from database import engine, get_db
from models import User, Article
from lambda_trigger import trigger_worker, get_queue_statistics, retry_article_job
from agents.title_agent import generate_titles

# --- CONFIGURATION ---
SECRET_KEY = "CHANGE_THIS_TO_A_SUPER_SECRET_KEY_IN_PRODUCTION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Initialize DB
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pro Content Engine API")

# CORS (Allow Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- SECURITY TOOLS ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def verify_password(plain_password, hashed_password):
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password, hashed_password)

def get_password_hash(password: str):
    if len(password.encode('utf-8')) > 72:
         raise HTTPException(status_code=400, detail="Password cannot exceed 72 bytes.")
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

# --- AUTH ROUTES ---

class UserSignup(BaseModel):
    username: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class GoogleAuthRequest(BaseModel):
    token: str

@app.post("/auth/signup", response_model=Token)
def signup(user: UserSignup, response: Response, db: Session = Depends(get_db)):
    logger.info(f"🔐 Signup attempt for email: {user.email}")
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        logger.warning(f"⚠️ Email already registered: {user.email}")
        raise HTTPException(status_code=400, detail="Email already registered")
    if not user.password:
        raise HTTPException(status_code=400, detail="Password is required")

    hashed_pw = get_password_hash(user.password)
    new_user = models.User(username=user.username, email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"✅ User created successfully: {new_user.id}")
    
    access_token = create_access_token(data={"sub": str(new_user.id)})
    refresh_token = create_refresh_token(data={"sub": str(new_user.id)})
    
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="lax", secure=False)
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": str(new_user.id), "username": new_user.username, "email": new_user.email}}

@app.post("/auth/login", response_model=Token)
def login(form_data: UserSignup, response: Response, db: Session = Depends(get_db)):
    logger.info(f"🔐 Login attempt for email: {form_data.email}")
    user = db.query(models.User).filter(models.User.email == form_data.email).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"⚠️ Failed login for: {form_data.email}")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    logger.info(f"✅ Login successful for user: {user.id}")
    
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, samesite="lax", secure=False)
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": str(user.id), "username": user.username, "email": user.email}}

@app.post("/auth/google", response_model=Token)
def google_login(payload: GoogleAuthRequest, response: Response, db: Session = Depends(get_db)):
    fake_google_email = "user@gmail.com" 
    fake_google_id = "12345_google"
    user = db.query(models.User).filter(models.User.email == fake_google_email).first()
    if not user:
        user = models.User(username=fake_google_email.split("@")[0], email=fake_google_email, google_id=fake_google_id)
        db.add(user)
        db.commit()
        db.refresh(user)
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True)
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": str(user.id), "username": user.username, "email": user.email}}

@app.post("/auth/refresh", response_model=Token)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
         raise HTTPException(status_code=401, detail="Refresh token missing")
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        new_access_token = create_access_token(data={"sub": str(user.id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})
        response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, samesite="lax", secure=False)
        return {"access_token": new_access_token, "token_type": "bearer", "user": {"id": str(user.id), "username": user.username, "email": user.email}}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# --- BACKGROUND TASK ---

async def trigger_worker_task(payload: dict):
    try:
        await trigger_worker(
            payload["article_id"], payload["query"], payload["category"],
            payload["target_length"], payload["source_count"]
        )
    except Exception as e:
        logger.error(f"❌ Background Trigger Failed: {e}")

# --- APP ROUTES ---

@app.post("/generate", response_model=schemas.ArticleResponse)
async def generate_article(
    request: schemas.ArticleCreateRequest, 
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    logger.info(f"📝 Creating new article for user: {current_user.id}")
    logger.info(f"   Query: {request.query_explanation[:50]}...")
    logger.info(f"   Category: {request.category}")
    logger.info(f"   Target Length: {request.target_length}")
    
    new_article = Article(
        id=uuid.uuid4(),
        user_id=current_user.id,
        raw_query=request.query_explanation,
        category=request.category,
        target_length=request.target_length,
        source_count=request.source_count,
        scheduled_at=request.scheduled_at,
        timezone=request.timezone,
        status="queued",
        topic=request.query_explanation[:50] + "..."
    )
    db.add(new_article)
    db.commit()
    db.refresh(new_article)
    
    logger.info(f"✅ Article created with ID: {new_article.id}")

    payload = {
        "article_id": str(new_article.id), "query": new_article.raw_query,
        "category": new_article.category, "target_length": new_article.target_length,
        "source_count": new_article.source_count
    }
    background_tasks.add_task(trigger_worker_task, payload)
    return new_article

@app.get("/stats")
def get_dashboard_stats(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info(f"📊 Stats request for user: {current_user.id}")
    stats = db.query(Article.status, func.count(Article.id)).filter(Article.user_id == current_user.id).group_by(Article.status).all()
    stats_map = {s: c for s, c in stats}
    result = {
        "total": sum(stats_map.values()),
        "processing": stats_map.get("processing", 0) + stats_map.get("queued", 0),
        "scheduled": stats_map.get("scheduled", 0),
        "completed": stats_map.get("completed", 0),
        "posted": stats_map.get("posted", 0),
    }
    logger.info(f"   Stats: {result}")
    return result

@app.get("/articles", response_model=List[schemas.ArticleResponse])
def get_articles(skip: int = 0, limit: int = 100, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info(f"📚 Articles list request for user: {current_user.id} (skip={skip}, limit={limit})")
    
    articles = db.query(Article).filter(Article.user_id == current_user.id).order_by(Article.created_at.desc()).offset(skip).limit(limit).all()
    
    logger.info(f"   Found {len(articles)} articles")
    return articles

@app.get("/articles/{article_id}")
def get_article_detail(article_id: uuid.UUID, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info(f"🔍 Article detail request for {article_id}")
    
    article = db.query(Article).options(
        joinedload(Article.sources),
        joinedload(Article.brief)
    ).filter(Article.id == article_id, Article.user_id == current_user.id).first()
    
    if not article: 
        raise HTTPException(status_code=404, detail="Article not found")
    
    return article

@app.post("/articles/{article_id}/retry", response_model=schemas.ArticleResponse)
async def retry_article(
    article_id: uuid.UUID,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retry a failed article"""
    article = db.query(Article).filter(
        Article.id == article_id,
        Article.user_id == current_user.id
    ).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if article.status not in ["failed"]:
        raise HTTPException(status_code=400, detail=f"Can only retry failed articles")
    
    if article.retry_count >= 3:
        raise HTTPException(status_code=400, detail="Maximum retry limit reached")
    
    payload = {
        "query": article.raw_query,
        "category": article.category,
        "target_length": article.target_length,
        "source_count": article.source_count
    }
    
    success = await retry_article_job(str(article.id), payload)
    
    if success:
        article.status = "queued"
        article.error_message = None
        article.retry_count += 1
        db.commit()
        db.refresh(article)
        return article
    else:
        raise HTTPException(status_code=500, detail="Failed to queue retry")

class ArticleUpdateRequest(BaseModel):
    content: Optional[str] = None
    topic: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None

@app.patch("/articles/{article_id}")
def update_article(
    article_id: uuid.UUID,
    updates: ArticleUpdateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    article = db.query(Article).filter(
        Article.id == article_id, 
        Article.user_id == current_user.id
    ).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if updates.content is not None:
        article.content = updates.content
    if updates.topic is not None:
        article.topic = updates.topic
    if updates.category is not None:
        article.category = updates.category
    if updates.status is not None:
        article.status = updates.status
    
    db.commit()
    db.refresh(article)
        
    return {"success": True, "message": "Article updated", "article": article}

@app.get("/health")
async def health_check():
    """Health check with queue stats"""
    queue_stats = await get_queue_statistics()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "queue": queue_stats
    }

@app.get("/queue/stats")
async def get_queue_stats(current_user: models.User = Depends(get_current_user)):
    """Get SQS queue statistics"""
    stats = await get_queue_statistics()
    return {"queue_name": "article-generation-queue", **stats}

@app.post("/generate/titles", response_model=List[schemas.ArticleTitle])
async def generate_article_titles(
    request: schemas.TitleGenerationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate title suggestions"""
    logger.info(f"🎯 Generating {request.count} titles for user: {current_user.id}")
    
    titles = await generate_titles(request.description, request.count)
    
    db_titles = []
    for title_text in titles:
        db_title = models.ArticleTitle(
            id=uuid.uuid4(),
            user_id=current_user.id,
            title=title_text,
            description=request.description,
            status="generated"
        )
        db.add(db_title)
        db_titles.append(db_title)
    
    db.commit()
    for t in db_titles:
        db.refresh(t)
    
    return db_titles

@app.patch("/titles/{title_id}/verify")
async def verify_title(
    title_id: uuid.UUID,
    request: schemas.TitleVerificationRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve/reject title"""
    title = db.query(models.ArticleTitle).filter(
        models.ArticleTitle.id == title_id,
        models.ArticleTitle.user_id == current_user.id
    ).first()
    
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")
    
    title.title = request.title
    title.status = request.status
    db.commit()
    db.refresh(title)
    
    return {"success": True, "title": title}

@app.post("/generate/batch")
async def generate_batch_articles(
    request: schemas.BatchGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Batch generate articles from approved titles"""
    logger.info(f"🚀 Batch generation: {len(request.title_ids)} titles")
    
    titles = db.query(models.ArticleTitle).filter(
        models.ArticleTitle.id.in_(request.title_ids),
        models.ArticleTitle.user_id == current_user.id
    ).all()
    
    if len(titles) != len(request.title_ids):
        raise HTTPException(status_code=400, detail="Some titles not found")
    
    created_articles = []
    
    for title_obj in titles:
        new_article = models.Article(
            id=uuid.uuid4(),
            user_id=current_user.id,
            raw_query=title_obj.title,
            category=request.category,
            target_length=request.target_length,
            source_count=request.source_count,
            scheduled_at=request.scheduled_at,
            timezone=request.timezone,
            status="queued",
            topic=title_obj.title
        )
        db.add(new_article)
        created_articles.append(new_article)
    
    db.commit()
    
    for article in created_articles:
        db.refresh(article)
        payload = {
            "article_id": str(article.id),
            "query": article.raw_query,
            "category": article.category,
            "target_length": article.target_length,
            "source_count": article.source_count
        }
        background_tasks.add_task(trigger_worker_task, payload)
    
    logger.info(f"✅ Created {len(created_articles)} articles and queued")
    
    return {
        "success": True,
        "message": f"Created {len(created_articles)} articles",
        "article_ids": [str(a.id) for a in created_articles]
    }