from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
import models
from routers import internal

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="NeuralGen API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

from routers import auth, articles, generation, campaigns, credits, api_keys, integrations, system

app.include_router(auth.router)
app.include_router(articles.router)
app.include_router(generation.router)
app.include_router(generation.titles_router)
app.include_router(campaigns.router)
app.include_router(credits.router)
app.include_router(api_keys.router)
app.include_router(integrations.router)
app.include_router(system.router)
app.include_router(internal.router)
