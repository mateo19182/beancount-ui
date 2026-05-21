"""Document upload, naming, and path management."""

import re
from pathlib import Path
from datetime import datetime


def save_document(
    file_bytes: bytes,
    filename: str,
    date_str: str,
    payee: str | None,
    narration: str | None,
    documents_dir: Path,
) -> tuple[bool, str, Path | None]:
    """Save a document with proper naming and organization.

    Documents are stored as: documents_dir/YYYY/MM/YYYY-MM-DD-payee-narration.ext

    Returns (success, message, relative_path_from_ledger_dir).
    """
    try:
        clean_name = _generate_filename(date_str, payee, narration, filename)
        target = _get_document_path(documents_dir, date_str, clean_name)

        if target.exists():
            timestamp = datetime.now().strftime("%H%M%S")
            target = target.with_stem(f"{target.stem}-{timestamp}")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file_bytes)

        # Return path relative to the ledger directory (parent of documents_dir)
        rel_path = target.relative_to(documents_dir.parent)
        return True, f"Document saved: {rel_path}", rel_path

    except Exception as e:
        return False, f"Error saving document: {e}", None


def _generate_filename(date_str: str, payee: str | None, narration: str | None, original: str) -> str:
    ext = Path(original).suffix.lower()
    parts = [date_str]

    payee_clean = _clean(payee)
    narration_clean = _clean(narration)

    if payee_clean:
        parts.append(payee_clean)
    if narration_clean and narration_clean != payee_clean:
        parts.append(narration_clean)

    base = "-".join(parts)[:100]
    return f"{base}{ext}"


def _get_document_path(documents_dir: Path, date_str: str, filename: str) -> Path:
    parts = date_str.split("-")
    year = parts[0]
    month = parts[1].zfill(2) if len(parts) > 1 else "01"
    return documents_dir / year / month / filename


def _clean(text: str | None) -> str:
    if not text:
        return ""
    cleaned = text.lower().strip()
    cleaned = re.sub(r"[^\w\s-]", "", cleaned)
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned
