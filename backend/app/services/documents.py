"""Extract readable text from uploaded documents (PDF, Word, plain text).

Mirrors ingestion.py (which handles notes/URLs): its only job is to turn a file
into a title + clean text string. Chunking/embedding/storage happen downstream.
"""

import io

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.errors import DocumentError
from app.logging_config import get_logger

logger = get_logger(__name__)

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def extract_text(filename: str, data: bytes) -> tuple[str, str]:
    """Return (title, text) from an uploaded file. Raises DocumentError on failure."""
    if not data:
        raise DocumentError("The uploaded file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise DocumentError(f"File is too large (max {MAX_FILE_BYTES // (1024 * 1024)} MB).")

    name = (filename or "").strip()
    lower = name.lower()

    if lower.endswith(".pdf"):
        text = _from_pdf(data)
    elif lower.endswith(".docx"):
        text = _from_docx(data)
    elif lower.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace")
    else:
        raise DocumentError("Unsupported file type. Upload a PDF, DOCX, TXT, or MD file.")

    cleaned = _clean(text)
    if not cleaned:
        raise DocumentError("No readable text found in the document.")

    title = name.rsplit(".", 1)[0] or "Untitled document"
    logger.info("document_extracted file=%r chars=%d", name, len(cleaned))
    return title, cleaned


def _from_pdf(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:  # pypdf raises a variety of parse errors
        raise DocumentError(f"Could not read PDF: {exc}") from exc


def _from_docx(data: bytes) -> str:
    try:
        doc = DocxDocument(io.BytesIO(data))
        return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as exc:
        raise DocumentError(f"Could not read Word document: {exc}") from exc


def _clean(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
