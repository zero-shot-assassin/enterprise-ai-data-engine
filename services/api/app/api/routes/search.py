import logging

from fastapi import APIRouter, Query
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue
)

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])
MODEL_NAME = settings.embedding_model
COLLECTION_NAME = "documents"

model = SentenceTransformer(MODEL_NAME)

@router.get("/search")
async def search(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Number of results to return"),
    source_filter: str | None = Query(None, description="Filter by source"),
):
    """
    Search for documents using vector similarity.
    
    Args:
        query: Search query text
        limit: Maximum number of results to return
        source: Optional filter by source (e.g., "github", "website")
    
    Returns:
        List of matching documents with similarity scores
    """
    logger.info(f"Searching for query: {query}")
    
    qdrant_client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    # Generate query embedding
    query_embedding = model.encode(query, convert_to_numpy=True).tolist()
    
    # Build filter if source is specified
    filters = None
    if source_filter:
        filters = Filter(
            must=[
                FieldCondition(
                    key="source",
                    match=MatchValue(value=source_filter)
                )
            ]
        )
    
    # Search in Qdrant
    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_embedding,
        query_filter=filters,
        limit=limit
    ).points
    
    # Format results
    formatted_results = []
    for result in results:
        formatted_results.append({
            "id": result.id,
            "score": result.score,
            "payload": result.payload
        })
    
    return {
        "query": query,
        "results": formatted_results,
        "count": len(formatted_results)
    }
