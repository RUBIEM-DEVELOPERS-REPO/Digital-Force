"""
Digital Force — RAG Retriever
Hybrid dense + sparse search with reranking over Qdrant.
"""

import logging
from typing import Optional
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    from qdrant_client import QdrantClient
    if settings.qdrant_use_cloud:
        _client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    else:
        _client = QdrantClient(path=settings.qdrant_local_path)
    return _client


def _get_embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("all-MiniLM-L6-v2")


_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = _get_embedder()
    return _embedder


async def retrieve(
    query: str,
    collection: str = "knowledge",
    top_k: int = 5,
    filter_metadata: Optional[dict] = None,
) -> list[dict]:
    """
    Retrieve semantically relevant documents from Qdrant.
    Returns list of {text, score, metadata} dicts.
    """
    try:
        client = _get_client()
        embedder = get_embedder()

        # Map collection alias to actual collection name
        collection_map = {
            "knowledge": settings.qdrant_knowledge_collection,
            "brand": settings.qdrant_brand_collection,
            "media": settings.qdrant_media_collection,
        }
        collection_name = collection_map.get(collection, settings.qdrant_knowledge_collection)

        query_vector = embedder.encode(query).tolist()

        from qdrant_client.models import Filter, FieldCondition, MatchValue
        qdrant_filter = None
        if filter_metadata:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filter_metadata.items()
            ]
            qdrant_filter = Filter(must=conditions) if conditions else None

        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        return [
            {
                "text": r.payload.get("text", ""),
                "score": r.score,
                "metadata": {k: v for k, v in r.payload.items() if k != "text"},
                "id": str(r.id),
            }
            for r in results
        ]

    except Exception as e:
        logger.warning(f"[RAG] Retrieval failed: {e}")
        return []


async def store(
    text: str,
    metadata: dict,
    collection: str = "knowledge",
    point_id: Optional[str] = None,
) -> str:
    """Store a text chunk with metadata in Qdrant."""
    import uuid
    from qdrant_client.models import PointStruct

    try:
        client = _get_client()
        embedder = get_embedder()

        collection_map = {
            "knowledge": settings.qdrant_knowledge_collection,
            "brand": settings.qdrant_brand_collection,
            "media": settings.qdrant_media_collection,
        }
        collection_name = collection_map.get(collection, settings.qdrant_knowledge_collection)

        vector = embedder.encode(text).tolist()
        pid = point_id or str(uuid.uuid4())

        payload = {"text": text, **metadata}
        client.upsert(
            collection_name=collection_name,
            points=[PointStruct(id=pid, vector=vector, payload=payload)]
        )
        return pid

    except Exception as e:
        logger.error(f"[RAG] Store failed: {e}")
        raise


async def ensure_collections():
    """Create Qdrant collections if they don't exist."""
    from qdrant_client.models import Distance, VectorParams
    client = _get_client()
    collections_to_create = [
        settings.qdrant_knowledge_collection,
        settings.qdrant_brand_collection,
        settings.qdrant_media_collection,
    ]
    existing = {c.name for c in client.get_collections().collections}
    for name in collections_to_create:
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=settings.qdrant_dimension, distance=Distance.COSINE),
            )
            logger.info(f"[RAG] Created collection: {name}")
