from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import budgets, chat, goals, transactions
from app.auth import demo_password_middleware
from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.models import Category

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # A fresh database (first boot, or an ephemeral disk after a redeploy)
    # gets the demo data so the agent has something to talk about.
    with SessionLocal() as db:
        if db.query(Category).count() == 0:
            from seed_data import reset_and_seed

            reset_and_seed(db)
    yield


app = FastAPI(title="Spendwise API", lifespan=lifespan)
app.state.demo_password = settings.demo_password

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(demo_password_middleware)

app.include_router(chat.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(goals.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/check")
def auth_check():
    """Protected no-op: 200 means the caller is in (or no password is set)."""
    return {"ok": True}


# The Flutter web build, when present, is served from the same origin so the
# demo is one URL. Mounted last so API routes take precedence.
static_dir = Path(settings.static_dir)
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
