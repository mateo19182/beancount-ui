"""FastAPI application for beancount-ui."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    banking,
    banks,
    charts,
    crypto,
    documents,
    health,
    investments,
    ledger_router,
    overview,
    transactions,
)

app = FastAPI(title="beancount-ui", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:1420",
        "http://127.0.0.1:1420",
        "tauri://localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ledger_router.router)
app.include_router(overview.router)
app.include_router(charts.router)
app.include_router(investments.router)
app.include_router(crypto.router)
app.include_router(banks.router)
app.include_router(transactions.router)
app.include_router(documents.router)
app.include_router(banking.router)
