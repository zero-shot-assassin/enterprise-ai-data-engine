import json
import io
import logging
from datetime import datetime
from pathlib import Path

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.core.config import settings
from app.core.storage import get_minio_client

logger = logging.getLogger(__name__)

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]
CHUNKS_BUCKET = "processed-chunks"


def chunk_markdown(md_text: str, source_meta: dict) -> list[dict]:
    """
    Split markdown into header-based chunks with rich metadata.
    """
    # 1. Split markdown into header-based chunks
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS, 
        strip_headers=False
    )

    header_chunks = header_splitter.split_text(md_text)

    # 2. Further split large sections into smaller chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=200
    )

    chunks = text_splitter.split_documents(header_chunks)

    # 3. Build the final payloads
    chunk_payloads = []

    for i, chunk in enumerate(chunks):

        # Determine if this chunk containers a md table
        is_table = any(
            line.strip().startswith("|") and "|" in line.strip()[1:]
            for line in chunk.page_content.splitlines()
        )
        chunk_payload = {
            "content": chunk.page_content,
            "metadata": {
                "source": source_meta.get("source"),
                "source_object": source_meta.get("source_object"),
                "chunk_index": i,
                "headers": chunk.metadata.get("headers", {}),
                "chunk_type": "table" if is_table else "text",
                "date": source_meta.get("date")
            }
        }
        chunk_payloads.append(chunk_payload)
    
    return chunk_payloads



def main():
    """
    Pull all .md files from processed-markdown,
    chunk them, and write .chunks.jsonl to processed-chunks.
    """

    # 1. Initialize MinIO client
    s3_client = get_minio_client()

    # 2. Ensure chunks bucket exists
    if not s3_client.bucket_exists(CHUNKS_BUCKET):
        s3_client.make_bucket(CHUNKS_BUCKET)
        logger.info("Created bucket: %s", CHUNKS_BUCKET)

    # 3. List objects in Silver bucket
    objects = s3_client.list_objects(
        settings.s3_bucket_processed,
        recursive=True
    )

    for obj in objects:

        # Skip objects with no name (directory markers, edge cases)
        if not obj.object_name:
            continue

        # Only process Markdown files
        if not obj.object_name.endswith(".md"):
            continue

        response = None

        try:
            # 4. Get object information
            stat = s3_client.stat_object(
                settings.s3_bucket_processed,
                obj.object_name
            )

            # 5. Download Markdown
            response = s3_client.get_object(
                settings.s3_bucket_processed,
                obj.object_name
            )

            md_text = response.read().decode("utf-8")

            # 6. Retrieve original document metadata
            object_metadata = stat.metadata or {}

            # MinIO custom metadata may use X-Amz-Meta- prefixes.
            normalized_metadata = {
                key.lower().removeprefix("x-amz-meta-"): value
                for key, value in object_metadata.items()
            }

            source_object = normalized_metadata.get(
                "source-object",
                obj.object_name.removesuffix(".md")
            )

            source_filename = normalized_metadata.get(
                "source-filename",
                Path(source_object).name
            )

            source_meta = {
                "source": source_filename,
                "source_object": source_object,
                "date": stat.last_modified.isoformat() if stat.last_modified else datetime.now().isoformat()
            }

            # 7. Chunk Markdown
            chunks = chunk_markdown(md_text, source_meta)

            # 8. Convert chunks into JSONL
            jsonl = "\n".join(
                json.dumps(chunk, ensure_ascii=False)
                for chunk in chunks
            )

            jsonl_bytes = jsonl.encode("utf-8")

            # 9. Upload JSONL to chunks bucket
            output_name = (
                f"{obj.object_name.removesuffix('.md')}.chunks.jsonl"
            )

            s3_client.put_object(
                bucket_name=CHUNKS_BUCKET,
                object_name=output_name,
                data=io.BytesIO(jsonl_bytes),
                length=len(jsonl_bytes),
                content_type="application/x-ndjson"
            )

            logger.info(
                "Document chunked: %s, chunks: %d",
                obj.object_name,
                len(chunks)
            )

        except Exception:
            logger.exception(
                "Failed to chunk document: %s",
                obj.object_name
            )
            raise

        finally:
            if response is not None:
                response.close()
                response.release_conn()


if __name__ == "__main__":
    main()