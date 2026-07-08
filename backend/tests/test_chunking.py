from app.config import settings
from app.services.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_short_text_is_a_single_chunk():
    chunks = chunk_text("A short note that fits comfortably in one chunk.")
    assert len(chunks) == 1
    assert "short note" in chunks[0]


def test_long_text_splits_into_multiple_chunks():
    paragraph = "This is a sentence that we repeat to build length. "
    text = "\n\n".join([paragraph * 10 for _ in range(6)])
    chunks = chunk_text(text)
    assert len(chunks) > 1
    # No chunk should wildly exceed the configured budget (allowing the overlap
    # carry-over to push slightly past the target).
    for chunk in chunks:
        assert len(chunk) <= settings.chunk_size_chars + settings.chunk_overlap_chars + 5


def test_oversized_single_paragraph_is_hard_split():
    giant = "x" * (settings.chunk_size_chars * 3)
    chunks = chunk_text(giant)
    assert len(chunks) >= 3
    # Same bound as the general case: overlap carry-over can push a packed chunk
    # up to size + overlap, but never unbounded.
    for chunk in chunks:
        assert len(chunk) <= settings.chunk_size_chars + settings.chunk_overlap_chars + 5
