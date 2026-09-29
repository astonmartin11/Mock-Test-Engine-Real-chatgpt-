from __future__ import annotations
from documents.embeddings import embed_one
from database.repositories.chunks import ChunkRepository

def retrieve(subject_id, query, limit=8):
    repo = ChunkRepository()
    merged = {}

    # Semantic retrieval is attempted first. If the embedding API is unavailable
    # or a document has no embeddings yet, lexical search remains functional.
    try:
        for row in repo.vector_search(subject_id, embed_one(query), limit):
            merged[str(row['id'])] = {
                **row,
                'score': 0.60 * float(row.get('semantic_score') or 0.0)
            }
    except Exception:
        pass

    for row in repo.keyword_search(subject_id, query, limit):
        key = str(row['id'])
        merged.setdefault(key, {**row, 'score': 0.0})
        merged[key]['score'] += 0.40 * float(row.get('lexical_score') or 0.0)

    return sorted(merged.values(), key=lambda x: x['score'], reverse=True)[:limit]
