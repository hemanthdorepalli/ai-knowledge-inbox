"""Chunking strategy: paragraph-aware packing with a character budget and overlap.

Rationale (see README for full tradeoff writeup): paragraphs are natural semantic
units, so we pack whole paragraphs into a chunk until we'd exceed `chunk_size_chars`,
then start a new chunk that repeats the trailing `chunk_overlap_chars` of the
previous chunk (so a fact split across a chunk boundary still has surrounding
context on both sides). A single paragraph longer than the budget is hard-split
on a fixed window, since we can't wait for a paragraph break that never comes.
"""

from app.config import settings


def chunk_text(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    size = settings.chunk_size_chars
    overlap = settings.chunk_overlap_chars

    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= size:
            units.append(paragraph)
        else:
            units.extend(_hard_split(paragraph, size, overlap))

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= size or not current:
            current = candidate
        else:
            chunks.append(current)
            carry_over = current[-overlap:] if overlap > 0 else ""
            current = f"{carry_over}\n\n{unit}" if carry_over else unit

    if current:
        chunks.append(current)

    return chunks


def _hard_split(text: str, size: int, overlap: int) -> list[str]:
    step = max(size - overlap, 1)
    return [text[i : i + size] for i in range(0, len(text), step)]
