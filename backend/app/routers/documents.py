from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.deps import state
from app.schemas.common import MessageResponse
from app.services.document_handler import save_document
from app.services.transaction_writer import (
    add_document_to_transaction,
    add_document_to_transaction_by_id,
    find_transaction_file,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])


def _resolve_document_path(rel_path: str) -> Path:
    config = state.config
    if not config.documents_dir:
        raise HTTPException(500, "Documents directory not configured")
    docs_root = config.documents_dir.resolve()
    target = (docs_root / rel_path).resolve()
    if not str(target).startswith(str(docs_root)):
        raise HTTPException(400, "Invalid document path")
    if not target.exists():
        raise HTTPException(404, "Document not found")
    return target


@router.get("/{path:path}")
def get_document(path: str):
    state.require_ledger()
    target = _resolve_document_path(path)
    return FileResponse(target)


@router.post("", response_model=MessageResponse)
async def upload_document(
    file: UploadFile = File(...),
    date: str = Form(""),
    payee: str = Form(""),
    narration: str = Form(""),
    transaction_id: str = Form(""),
    attach: bool = Form(True),
):
    config = state.config
    ledger = state.require_ledger()
    if not config.documents_dir:
        raise HTTPException(500, "Documents directory not configured")

    content = await file.read()
    ok, message, rel_path = save_document(
        content,
        file.filename or "document",
        date or "1970-01-01",
        payee or None,
        narration or None,
        config.documents_dir,
    )
    if not ok:
        return MessageResponse(success=False, message=message)

    if attach and transaction_id:
        ok2, msg2 = add_document_to_transaction_by_id(
            config.ledger_dir, transaction_id, str(rel_path)
        )
        if ok2:
            state.reload_ledger()
            return MessageResponse(success=True, message=msg2)

    if attach and payee and date:
        target = find_transaction_file(config.ledger_dir, date, payee, narration or None)
        if target:
            ok2, msg2 = add_document_to_transaction(
                target, date, payee, narration or "", str(rel_path)
            )
            if ok2:
                state.reload_ledger()
                return MessageResponse(success=True, message=msg2)

    return MessageResponse(success=True, message=message)
