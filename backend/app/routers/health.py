from fastapi import APIRouter

from app.deps import state

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "ledger_loaded": state.ledger is not None,
        "ledger_path": str(state.config.ledger_path) if state.config.ledger_path else None,
    }
