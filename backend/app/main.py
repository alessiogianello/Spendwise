from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import budgets, chat, goals, transactions
from app.db import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Spendwise API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(goals.router)


@app.get("/health")
def health():
    return {"status": "ok"}
