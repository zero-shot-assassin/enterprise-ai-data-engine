import json
import logging
import uuid
from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.storage import get_minio_client
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
)

logger = logging.getLogger(__name__)
COLLECTION_NAME = "documents"
MODEL_NAME = settings.embedding_model


def embed_chunk(content: str, model: SentenceTransformer) -> list[float]:
    """
    Embed a chunk of text using the provided model.
    Generate 384-dimensional embeddings.
    
    Args:
        content: The text content to embed
        model: The SentenceTransformer model to use
        
    Returns:
        List of float embeddings (384 dimensions)
    """
    return model.encode(content, convert_to_numpy=True).tolist()


def upsert_chunks(chunks: list[dict], model: SentenceTransformer) -> None:
    """
    Upsert chunks into Qdrant collection.
    
    Args:
        chunks: List of chunk dictionaries with 'id', 'content', and 'metadata'
        model: The SentenceTransformer model to use
    """
    qdrant_client = QdrantClient(
        host=settings.qdrant_host, 
        port=settings.qdrant_port
    )

    # Ensure the collection exists
    if not qdrant_client.collection_exists(COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE
            )
        )
    
    # For each chunk, embed and upsert
    points = []
    for chunk in chunks:
        embedding = embed_chunk(chunk["content"], model)
        # Generate UUID from composite key for unique point ID
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{chunk['metadata']['source_object']}-{chunk['metadata']['chunk_index']}"))
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "content": chunk["content"],
                    **chunk["metadata"]
                }
            )
        )
    
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    logger.info(f"Upserted {len(points)} chunks to Qdrant collection '{COLLECTION_NAME}'")


def main():
    """
    Pull all .chunks.jsonl from processed-chunks, embed, upsert to Qdrant.
    """
    model = SentenceTransformer(MODEL_NAME)
    processed_chunks = get_minio_client().list_objects("processed-chunks")
    for chunk in processed_chunks:
        if chunk.object_name and chunk.object_name.endswith(".chunks.jsonl"):
            chunk_data = None
            try:
                chunk_data = get_minio_client().get_object("processed-chunks", chunk.object_name)
                chunks = [json.loads(line) for line in chunk_data.read().decode("utf-8").split("\n") if line.strip()]
                upsert_chunks(chunks, model)
            finally:
                if chunk_data:
                    chunk_data.close()
                    chunk_data.release_conn()

if __name__ == "__main__":
    main()