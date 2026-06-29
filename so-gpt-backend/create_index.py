"""
AI Search Index — Creation Script

Creates (or recreates) the so-gpt-index in Azure AI Search.
Run once before the first ingestion. Safe to re-run — uses create_or_update_index.

Usage:
    python create_index.py                # create / update index schema
    python create_index.py --recreate     # drop and recreate (loses all data)

Vector dimension: 3072  (text-embedding-3-large)
Semantic config:  "default"  (matches SEARCH_SEMANTIC_CONFIG in config.py)
"""
from __future__ import annotations

import argparse
import logging
import sys

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VECTOR_DIMENSIONS = 3072


def _build_index():
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.indexes.models import (
        HnswAlgorithmConfiguration,
        SearchField,
        SearchFieldDataType,
        SearchIndex,
        SearchableField,
        SemanticConfiguration,
        SemanticField,
        SemanticPrioritizedFields,
        SemanticSearch,
        SimpleField,
        VectorSearch,
        VectorSearchProfile,
    )
    from azure.core.credentials import AzureKeyCredential

    client = SearchIndexClient(
        endpoint=config.SEARCH_ENDPOINT,
        credential=AzureKeyCredential(config.SEARCH_API_KEY),
    )

    fields = [
        SimpleField(
            name="chunk_id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True,
        ),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            analyzer_name="de.microsoft",
        ),
        SearchableField(
            name="document_title",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="page_number",
            type=SearchFieldDataType.Int32,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="source_file",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="source_url",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="language",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="business_area",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="document_type",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="last_modified",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        SimpleField(
            name="topic",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SearchField(
            name="allowed_groups",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=VECTOR_DIMENSIONS,
            vector_search_profile_name="hnsw-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo")],
        profiles=[VectorSearchProfile(
            name="hnsw-profile",
            algorithm_configuration_name="hnsw-algo",
        )],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="default",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")],
                    title_field=SemanticField(field_name="document_title"),
                    keywords_fields=[SemanticField(field_name="business_area")],
                ),
            )
        ]
    )

    index = SearchIndex(
        name=config.SEARCH_INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    return client, index


def main(recreate: bool = False) -> None:
    if not config.SEARCH_ENDPOINT or not config.SEARCH_API_KEY:
        logger.error("SEARCH_ENDPOINT and SEARCH_API_KEY must be set in .env")
        sys.exit(1)

    client, index = _build_index()

    if recreate:
        try:
            client.delete_index(config.SEARCH_INDEX_NAME)
            logger.info("Deleted index: %s", config.SEARCH_INDEX_NAME)
        except Exception as exc:
            logger.warning("Could not delete index (may not exist): %s", exc)

    result = client.create_or_update_index(index)
    logger.info(
        "Index ready: %s — %d fields, vector dim=%d",
        result.name,
        len(result.fields),
        VECTOR_DIMENSIONS,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update the S.O. GPT AI Search index")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate the index (all indexed documents will be lost)",
    )
    main(recreate=parser.parse_args().recreate)
