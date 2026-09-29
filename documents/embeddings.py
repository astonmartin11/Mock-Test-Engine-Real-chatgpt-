from __future__ import annotations

from functools import lru_cache
from google import genai
from google.genai import types

from config import get_env, models

EMBED_DIMENSION = 384

@lru_cache(maxsize=1)
def client():
    return genai.Client(api_key=get_env("GEMINI_API_KEY"))

def _normalize(values):
    values = list(values or [])
    if len(values) != EMBED_DIMENSION:
        # The database schema currently uses vector(384). Gemini Embedding 2
        # supports a flexible output size, including 384.
        raise RuntimeError(
            f"Expected {EMBED_DIMENSION}-dimensional embedding, got {len(values)}."
        )
    return [float(x) for x in values]

def embed_one(text: str) -> list[float]:
    result = client().models.embed_content(
        model=models()["embedding"],
        contents=(
            "task: search result | query: " + text
            if text else "task: search result | query: none"
        ),
        config=types.EmbedContentConfig(output_dimensionality=EMBED_DIMENSION),
    )
    return _normalize(result.embeddings[0].values)

def embed_texts(texts: list[str]) -> list[list[float]]:
    # Keep this conservative on the zero-cost tier. Embeddings are generated
    # one item at a time and should be cached at the document/job level later.
    return [embed_one(text) for text in texts]
