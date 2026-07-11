"""Ingest the ROCm/HIP corpus into Qdrant.

Run once (after setting QDRANT_URL, QDRANT_API_KEY, FIREWORKS_API_KEY in .env):

    cd backend && python -m app.knowledge.ingest

Idempotent: recreates the collection each run. Embeds the seed corpus with the
Fireworks embedding model and upserts one point per chunk (payload: text, source).
"""
from __future__ import annotations

import sys

from app.config import settings
from app.knowledge.corpus import SEED_DOCS
from app.knowledge.fetch_docs import fetch_web_docs
from app.services import fireworks_service


def ingest(include_web: bool = True) -> int:
    if not settings.qdrant_url:
        print("QDRANT_URL is not set — add it to backend/.env first.")
        return 1
    if not settings.fireworks_enabled:
        print("FIREWORKS_API_KEY is not set — needed for embeddings.")
        return 1

    from qdrant_client import QdrantClient, models

    docs = list(SEED_DOCS)
    if include_web:
        print("Fetching live ROCm/HIP docs ...")
        web = fetch_web_docs()
        print(f"  +{len(web)} chunks from {len({d['source'] for d in web})} live pages")
        docs += web

    texts = [d["text"] for d in docs]
    print(f"Embedding {len(texts)} chunks with {settings.fireworks_embedding_model} ...")
    vectors = fireworks_service.embed(texts)
    if not vectors:
        print("Embedding failed — check the Fireworks key/model.")
        return 1
    dim = len(vectors[0])

    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
    print(f"Recreating collection '{settings.knowledge_collection}' (dim={dim}) ...")
    client.recreate_collection(
        collection_name=settings.knowledge_collection,
        vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
    )
    client.upsert(
        collection_name=settings.knowledge_collection,
        points=[
            models.PointStruct(id=i, vector=vectors[i],
                               payload={"text": docs[i]["text"], "source": docs[i]["source"]})
            for i in range(len(docs))
        ],
    )
    print(f"Ingested {len(docs)} chunks into Qdrant "
          f"({len(SEED_DOCS)} curated + {len(docs) - len(SEED_DOCS)} live). Knowledge base is live.")
    return 0


if __name__ == "__main__":
    sys.exit(ingest())
