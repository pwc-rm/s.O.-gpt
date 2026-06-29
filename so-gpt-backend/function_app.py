"""
Azure Function — Blob Trigger Ingestion

Fires automatically when a document is uploaded to the 'documents' container.
Full pipeline per upload: extract → chunk → embed → index in AI Search.

Supported formats: .pdf, .docx, .pptx, .xlsx
Unsupported files are silently skipped.
On failure, Azure retries up to 5 times with exponential backoff.
"""
from __future__ import annotations

import logging
from pathlib import Path

import azure.functions as func

import ingestion

app = func.FunctionApp()


@app.blob_trigger(
    arg_name="blob",
    path="documents/{name}",
    connection="BLOB_CONNECTION_STRING",
)
def ingest_on_upload(blob: func.InputStream, name: str) -> None:
    logging.info("Blob uploaded: %s (%d bytes)", name, blob.length)

    if Path(name).suffix.lower() not in ingestion.SUPPORTED_EXTENSIONS:
        logging.info("Skipping unsupported file type: %s", name)
        return

    count = ingestion.ingest_blob(blob_name=name)
    logging.info("Done: %s → %d chunks indexed", name, count)
