import numpy as np

from app.services.vector_store import VectorIndex


def test_empty_index_returns_no_matches():
    index = VectorIndex()
    assert index.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=3) == []


def test_search_ranks_by_cosine_similarity():
    index = VectorIndex()
    index.add(1, np.array([1.0, 0.0, 0.0], dtype=np.float32))  # closest to query
    index.add(2, np.array([0.0, 1.0, 0.0], dtype=np.float32))  # orthogonal
    index.add(3, np.array([0.9, 0.1, 0.0], dtype=np.float32))  # near query

    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    results = index.search(query, top_k=3)

    ranked_ids = [chunk_id for chunk_id, _ in results]
    assert ranked_ids[0] == 1  # exact match ranks first
    assert ranked_ids[1] == 3  # near match second
    assert ranked_ids[2] == 2  # orthogonal last
    # Scores are cosine similarities, so the top score is ~1.0.
    assert results[0][1] > 0.99


def test_top_k_caps_result_count():
    index = VectorIndex()
    for i in range(5):
        vec = np.zeros(3, dtype=np.float32)
        vec[i % 3] = 1.0
        index.add(i, vec)

    results = index.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=2)
    assert len(results) == 2


def test_magnitude_does_not_affect_ranking():
    # Cosine similarity is scale-invariant: a longer vector in the same
    # direction should not outrank a shorter one pointing more at the query.
    index = VectorIndex()
    index.add(1, np.array([10.0, 10.0, 0.0], dtype=np.float32))  # 45 degrees off
    index.add(2, np.array([1.0, 0.0, 0.0], dtype=np.float32))    # aligned

    results = index.search(np.array([1.0, 0.0, 0.0], dtype=np.float32), top_k=2)
    assert results[0][0] == 2
