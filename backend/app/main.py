from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401 — ensure models are registered before create_all

# Create tables on startup. For a single-user demo this is fine; in prod use Alembic.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Document Processing System",
    description="Upload invoices and purchase orders, extract structured data, validate, review.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/models")
def list_models():
    from google import genai
    client = genai.Client(api_key=settings.gemini_api_key)
    models = client.models.list()
    return {"models": [m.name for m in models]}

app.include_router(api_router)
