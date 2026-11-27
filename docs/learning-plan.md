> 🏗️
>
> **Objective:** Build a platform-agnostic, streaming and orchestrated data pipeline that ingests complex agricultural PDFs and live hardware telemetry, versions the data in an Apache Iceberg lakehouse, and serves it to AI agents via Qdrant.

## 📅 High-level roadmap

| Week | Timeline | Core focus | Tech stack |
| --- | --- | --- | --- |
| 1 | Days 1–7 | Advanced extraction and vector operations | Docker, FastAPI, MinIO, Redis, Celery, Docling, Qdrant |
| 2 | Days 8–14 | Orchestration and AI lakehouse | Prefect, DuckDB, Apache Iceberg (Silver and Gold layers) |
| 3 | Days 15–21 | Real-time event streaming | Eclipse Mosquitto (MQTT), Redpanda (Kafka), Pydantic |
| 4 | Days 22–28 | Quality, validation and handoff | Great Expectations, DVC, MCP (Model Context Protocol) |

## 🛠️ Week 1: Advanced Extraction & Vector Ops

*Decouple parsing from the API and master layout-aware chunking.*

### Day 1: The Local Infrastructure Stack

- [x]  Write `docker-compose.yml` with FastAPI, Redis, MinIO and Qdrant.
- [x]  Verify private Docker network communication.

### Day 2: The Ingestion API & Object Storage

- [x]  Build a FastAPI `POST /upload` endpoint.
- [x]  Write file-upload logic to MinIO (Bronze layer).
- [x]  Push the extraction task to a Redis queue.

### Day 3: The Asynchronous Docling Worker

- [x]  Set up a Celery worker container listening to Redis.
- [x]  Integrate Docling `DocumentConverter` to parse PDFs to Markdown.

### Day 4: Markdown Checkpointing

- [x]  Update the worker to save Docling Markdown back to MinIO in the `processed-markdown` bucket.

### Day 5: Structural Chunking

- [x]  Create `app/worker/chunking.py` with chunking logic and `__main__` entry point.
- [x]  Split by headers using `MarkdownHeaderTextSplitter`, preserving tables.
- [x]  Attach rich metadata—source, date and chunk type—to each segment.
- [x]  Write chunks to `processed-chunks` bucket as `.chunks.jsonl`.

### Day 6: Embeddings & Qdrant Upsert

- [ ]  Generate local vector embeddings, for example with `all-MiniLM-L6-v2`.
- [ ]  Bulk-upsert chunks and metadata payloads into Qdrant.

### Day 7: The Retrieval API & End-to-End Testing

- [ ]  Build a FastAPI `GET /search` endpoint.
- [ ]  Implement payload-filtered Qdrant vector search.
- [ ]  Test the full path: upload PDF → process → search.

## 🌊 Week 2: Orchestration & the AI Lakehouse

*Move from raw queues to stateful pipelines and open table formats.*

### Day 8: The Orchestrator Upgrade

- [ ]  Add Prefect to `docker-compose.yml`.
- [ ]  Write a dummy `@flow` and `@task` to verify the dashboard and logging.

### Day 9: The Bronze-to-Silver Flow

- [ ]  Convert the Week 1 Celery extraction into a Prefect flow.
- [ ]  Add exception handling and retries for Docling timeouts.

### Day 10: The Iceberg Silver Layer

- [ ]  Install `duckdb` v1.4.0 or later.
- [ ]  Write SQL execution to insert parsed Markdown and metadata into an Apache Iceberg table on MinIO.

### Day 11: Incremental Processing Logic

- [ ]  Write a DuckDB query to select only new Markdown files using `WHERE processed_at > last_run`.
- [ ]  Integrate incremental selection into a Prefect task.

### Day 12: The Gold Layer & Semantic Chunking

- [ ]  Process incremental text through the chunking script.
- [ ]  Write structural chunks to the Iceberg Gold layer table.

### Day 13: The Qdrant Sync

- [ ]  Write a Prefect task to read from the Gold Iceberg table.
- [ ]  Embed and upsert directly into Qdrant.

### Day 14: Observability & Alerting

- [ ]  Configure Prefect state handlers.
- [ ]  Connect a Telegram bot webhook to send mobile alerts on pipeline failures.

## ⚡ Week 3: Real-Time Event Streaming

*Handle thousands of live MQTT hardware telemetry packets instantly.*

### Day 15: The Streaming Infrastructure Stack

- [ ]  Add Eclipse Mosquitto (MQTT) to the Docker stack.
- [ ]  Add Redpanda (Kafka alternative) to the Docker stack.

### Day 16: The MQTT-to-Kafka Bridge

- [ ]  Write a Python service using `paho-mqtt` and `confluent-kafka`.
- [ ]  Forward `agripad/telemetry/#` payloads into the Redpanda `raw_soil` topic.

### Day 17: Stream Validation & Dead-Letter Queues

- [ ]  Write a consumer script to validate JSON via Pydantic, including checks such as pH limits.
- [ ]  Route bad or corrupted packets to a dead-letter topic.

### Day 18: Streaming to the Iceberg Lakehouse

- [ ]  Implement micro-batching in the consumer, for example every 500 records or 5 seconds.
- [ ]  Append micro-batches directly to the Iceberg lakehouse using DuckDB.

### Day 19: Event-Driven AI Triggers

- [ ]  Add a consumer condition to trigger a Prefect RAG flow when a sensor detects a critical threshold.
- [ ]  Push payload context to an external webhook or alert system.

### Day 20: The Telemetry Vector Sync (Gold Layer)

- [ ]  Write a daily Prefect task to aggregate 24-hour telemetry per device.
- [ ]  Generate an LLM text summary of the data and embed it into Qdrant.

### Day 21: High-Volume Stress Testing

- [ ]  Write a multithreaded Python load tester.
- [ ]  Send 10,000 simulated JSON payloads per second into Mosquitto and monitor latency.

## 🛡️ Week 4: Quality, Validation & Handoff

*Make the data trusted and accessible to AI agents.*

### Day 22: Data Version Control (DVC) Setup

- [ ]  Initialize DVC in the project repository.
- [ ]  Version the baseline LLM fine-tuning corpora on MinIO.

### Day 23: Structured Data Validation

- [ ]  Implement Great Expectations for the telemetry stream.
- [ ]  Define strict data-quality suites for missing values and schema drift.

### Day 24: Unstructured Data Quality Metrics

- [ ]  Write a Prefect task to validate Qdrant chunks, including checks for empty strings and corrupted metadata.

### Day 25: Model Context Protocol (MCP) Server

- [ ]  Wrap Qdrant search and Iceberg DuckDB queries in an MCP server.
- [ ]  Expose these endpoints securely to agent frameworks.

### Day 26: Agentic Integration (LangGraph/LangChain)

- [ ]  Connect existing WhatsApp and Telegram bots to the new MCP server or API.
- [ ]  Test agent retrieval against the new Qdrant deployment.

### Day 27: CI/CD for Data Pipelines

- [ ]  Write GitHub Actions workflows to test Prefect flows on push.
- [ ]  Automate Docker image builds for the Celery and Prefect workers.

### Day 28: Architecture Documentation & Handover

- [ ]  Document data lineage from MinIO to Qdrant.
- [ ]  Finalize runbooks for restarting Redpanda and Prefect.
