"""
Ingestion Pipeline

Processes documents from Azure Blob Storage into the Azure AI Search index.
Run once during setup, then again whenever documents are added or updated.

Extraction strategy (hybrid):
  .docx / .pptx / .xlsx  →  markitdown  (local, free, no API call)
  .pdf                   →  Azure Document Intelligence Layout API (OCR-capable)

Full pipeline per document:
  1. Download from Blob Storage
  2. Extract text + structure → Markdown
  3. Chunk Markdown (heading-aware semantic chunking)
  4. Embed each chunk via Azure OpenAI text-embedding-3-large
  5. Upload chunks to Azure AI Search index

Usage:
  python ingestion.py                    # index all blobs in the configured container
  python ingestion.py --file foo.pdf     # index a single file
"""
from __future__ import annotations

import argparse
import logging
import uuid
from pathlib import Path

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx"}
PDF_EXTENSION = ".pdf"
SUPPORTED_EXTENSIONS = OFFICE_EXTENSIONS | {PDF_EXTENSION}


# ── Step 1: Blob Storage ──────────────────────────────────────────────────────

def list_blobs() -> list[str]:
    """Returns blob names in the configured container (supported file types only)."""
    from azure.storage.blob import BlobServiceClient
    client = BlobServiceClient.from_connection_string(config.BLOB_CONNECTION_STRING)
    container = client.get_container_client(config.BLOB_CONTAINER_NAME)
    return [
        b.name for b in container.list_blobs()
        if Path(b.name).suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def download_blob(blob_name: str) -> tuple[bytes, str]:
    """Downloads a blob and returns (raw bytes, last_modified ISO 8601 string)."""
    from azure.storage.blob import BlobServiceClient
    client = BlobServiceClient.from_connection_string(config.BLOB_CONNECTION_STRING)
    blob = client.get_blob_client(config.BLOB_CONTAINER_NAME, blob_name)
    properties = blob.get_blob_properties()
    data = blob.download_blob().readall()
    return data, properties.last_modified.isoformat()


# ── Step 2: Extraction → Markdown ─────────────────────────────────────────────

def extract_markdown(file_bytes: bytes, filename: str) -> str:
    """
    Converts a document to Markdown using the appropriate extractor:
      - .docx / .pptx / .xlsx  →  markitdown (Microsoft, local, no cost)
      - .pdf                   →  Azure Document Intelligence Layout API (handles OCR)
    """
    ext = Path(filename).suffix.lower()

    if ext in OFFICE_EXTENSIONS:
        return _extract_with_markitdown(file_bytes, ext)
    elif ext == PDF_EXTENSION:
        return _extract_with_document_intelligence(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}")


def _extract_with_markitdown(file_bytes: bytes, extension: str) -> str:
    """
    Uses Microsoft's markitdown library to convert Office documents to Markdown.
    Handles: .docx (text, tables, headings), .pptx (slides), .xlsx (sheets as tables).
    No API call — runs locally.
    """
    import tempfile
    import os
    from markitdown import MarkItDown

    md = MarkItDown()

    # markitdown works on file paths, not bytes — write to a temp file
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        result = md.convert(tmp_path)
        return result.text_content
    finally:
        os.unlink(tmp_path)


def _extract_with_document_intelligence(file_bytes: bytes) -> str:
    """
    Uses Azure Document Intelligence Layout API to extract PDFs as Markdown.
    Handles both machine-readable and scanned PDFs (OCR).
    Preserves tables, headings, and multi-column layouts.

    Requires DOCINTEL_ENDPOINT + DOCINTEL_API_KEY in .env.
    """
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
    from azure.core.credentials import AzureKeyCredential

    client = DocumentIntelligenceClient(
        endpoint=config.DOCINTEL_ENDPOINT,
        credential=AzureKeyCredential(config.DOCINTEL_API_KEY),
    )
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        body=AnalyzeDocumentRequest(bytes_source=file_bytes),
        output_content_format="markdown",
    )
    return poller.result().content


# ── Step 3: Chunking ──────────────────────────────────────────────────────────

def chunk_markdown(
    markdown: str,
    document_title: str,
    source_file: str,
    source_url: str = "",
    language: str = "de",
    business_area: str = "",
    document_type: str = "",
    topic: str = "",
    last_modified: str = "",
) -> list[dict]:
    """
    Splits Markdown into chunks for indexing.

    Strategy: heading-aware semantic chunking.
    - Split on H1/H2/H3 headings to keep sections together
    - Max ~800 tokens per chunk (~3200 chars)
    - Carry last 200 chars of previous chunk as overlap into the next

    TODO: tune MAX_CHUNK_CHARS and OVERLAP_CHARS based on retrieval
          quality testing in Phase 5.
    """
    import re

    MAX_CHUNK_CHARS = 3200
    OVERLAP_CHARS = 200

    sections = re.split(r"(?=\n#{1,3} )", markdown)
    sections = [s.strip() for s in sections if s.strip()]

    chunks: list[dict] = []
    page_counter = 1
    overlap_text = ""

    for section in sections:
        text = (overlap_text + "\n\n" + section).strip() if overlap_text else section

        if len(text) <= MAX_CHUNK_CHARS:
            chunks.append(_make_chunk(
                content=text,
                document_title=document_title,
                page_number=page_counter,
                source_file=source_file,
                source_url=source_url,
                language=language,
                business_area=business_area,
                document_type=document_type,
                topic=topic,
                last_modified=last_modified,
                allowed_groups=[],
            ))
            overlap_text = text[-OVERLAP_CHARS:] if len(text) > OVERLAP_CHARS else text
        else:
            paragraphs = text.split("\n\n")
            current = ""
            for para in paragraphs:
                if len(current) + len(para) > MAX_CHUNK_CHARS and current:
                    chunks.append(_make_chunk(
                        content=current.strip(),
                        document_title=document_title,
                        page_number=page_counter,
                        source_file=source_file,
                        source_url=source_url,
                        language=language,
                        business_area=business_area,
                        document_type=document_type,
                        topic=topic,
                        last_modified=last_modified,
                        allowed_groups=[],
                    ))
                    overlap_text = current[-OVERLAP_CHARS:]
                    current = overlap_text + "\n\n" + para
                    page_counter += 1
                else:
                    current = (current + "\n\n" + para).strip()
            if current:
                chunks.append(_make_chunk(
                    content=current.strip(),
                    document_title=document_title,
                    page_number=page_counter,
                    source_file=source_file,
                    source_url=source_url,
                    language=language,
                    business_area=business_area,
                    document_type=document_type,
                    topic=topic,
                    last_modified=last_modified,
                    allowed_groups=[],
                ))

        page_counter += 1

    return chunks


def _make_chunk(content: str, **metadata) -> dict:
    return {"chunk_id": str(uuid.uuid4()), "content": content, **metadata}


# ── Step 4: Embedding ─────────────────────────────────────────────────────────

def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Adds content_vector to each chunk via Azure OpenAI text-embedding-3-large.
    Processes in batches of 16 to stay within API limits.
    """
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=config.OPENAI_ENDPOINT,
        api_key=config.OPENAI_API_KEY,
        api_version=config.OPENAI_API_VERSION,
    )

    BATCH_SIZE = 16
    texts = [c["content"] for c in chunks]
    vectors: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i: i + BATCH_SIZE]
        response = client.embeddings.create(
            input=batch,
            model=config.OPENAI_EMBEDDING_DEPLOYMENT,
        )
        vectors.extend(item.embedding for item in response.data)
        logger.info("Embedded %d/%d chunks", min(i + BATCH_SIZE, len(texts)), len(texts))

    for chunk, vector in zip(chunks, vectors):
        chunk["content_vector"] = vector

    return chunks


# ── Step 5: Indexing ──────────────────────────────────────────────────────────

def index_chunks(chunks: list[dict]) -> None:
    """
    Uploads embedded chunks to Azure AI Search in batches.
    Index schema must exist before calling this (see Schlachtplan_Azure_Setup.md, Schritt 4).
    """
    from azure.search.documents import SearchClient
    from azure.core.credentials import AzureKeyCredential

    client = SearchClient(
        endpoint=config.SEARCH_ENDPOINT,
        index_name=config.SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(config.SEARCH_API_KEY),
    )

    BATCH_SIZE = 100
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i: i + BATCH_SIZE]
        result = client.upload_documents(documents=batch)
        succeeded = sum(1 for r in result if r.succeeded)
        logger.info(
            "Indexed batch %d–%d: %d/%d succeeded",
            i, i + len(batch), succeeded, len(batch),
        )


# ── Full pipeline ─────────────────────────────────────────────────────────────

def ingest_blob(
    blob_name: str,
    document_title: str | None = None,
    business_area: str = "",
    document_type: str = "",
    topic: str = "",
    language: str = "de",
) -> int:
    """
    Runs the full ingestion pipeline for a single blob.
    Returns the number of chunks indexed.
    """
    ext = Path(blob_name).suffix.lower()
    extractor = "markitdown" if ext in OFFICE_EXTENSIONS else "Document Intelligence"
    logger.info("Ingesting %s via %s", blob_name, extractor)

    title = document_title or Path(blob_name).stem.replace("_", " ")
    file_bytes, last_modified = download_blob(blob_name)
    markdown = extract_markdown(file_bytes, blob_name)
    chunks = chunk_markdown(
        markdown=markdown,
        document_title=title,
        source_file=blob_name,
        language=language,
        business_area=business_area,
        document_type=document_type,
        topic=topic,
        last_modified=last_modified,
    )
    chunks = embed_chunks(chunks)
    index_chunks(chunks)

    logger.info("Done: %s → %d chunks indexed", blob_name, len(chunks))
    return len(chunks)


def run_all() -> None:
    """Indexes all supported blobs in the configured container."""
    blobs = list_blobs()
    logger.info("Found %d blobs to index", len(blobs))
    total = 0
    for blob in blobs:
        try:
            total += ingest_blob(blob)
        except Exception as exc:
            logger.error("Failed to ingest %s: %s", blob, exc)
    logger.info("Ingestion complete: %d total chunks indexed", total)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S.O. GPT Ingestion Pipeline")
    parser.add_argument("--file", help="Index a single blob by name")
    parser.add_argument("--title", help="Document title (optional)")
    parser.add_argument("--area", default="", help="Business area tag (e.g. HR, IT, Legal)")
    parser.add_argument("--type", default="", help="Document type tag (e.g. Richtlinie, FAQ, Prozess)")
    parser.add_argument("--topic", default="", help="Topic tag (e.g. Urlaub, Datenschutz, Passwort)")
    parser.add_argument("--lang", default="de", help="Language (default: de)")
    args = parser.parse_args()

    if args.file:
        ingest_blob(args.file, args.title, args.area, args.type, args.topic, args.lang)
    else:
        run_all()
