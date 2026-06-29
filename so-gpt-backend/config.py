import os
from dotenv import load_dotenv

load_dotenv()

# ── Azure OpenAI ──────────────────────────────────────────────────────────────
# TODO: Architektur sieht AI Foundry AI Gateway vor (Rate Limiting, Token Visibility,
#       Model Routing GPT-4o ↔ GPT-4.1). Für den Showcase rufen wir Azure OpenAI direkt an.
#       Umstellung: OPENAI_ENDPOINT auf die AI Gateway URL zeigen lassen (kein Code-Change).
OPENAI_ENDPOINT: str = os.getenv("OPENAI_ENDPOINT", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_CHAT_DEPLOYMENT: str = os.getenv("OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv("OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
OPENAI_QUERY_REWRITE_DEPLOYMENT: str = os.getenv("OPENAI_QUERY_REWRITE_DEPLOYMENT", "gpt-4.1-mini")
OPENAI_API_VERSION: str = os.getenv("OPENAI_API_VERSION", "2024-08-01-preview")

# ── Azure AI Search ───────────────────────────────────────────────────────────
SEARCH_ENDPOINT: str = os.getenv("SEARCH_ENDPOINT", "")
SEARCH_API_KEY: str = os.getenv("SEARCH_API_KEY", "")
SEARCH_INDEX_NAME: str = os.getenv("SEARCH_INDEX_NAME", "so-gpt-index")
SEARCH_SEMANTIC_CONFIG: str = "default"

# ── Azure Cosmos DB (Session Store) ──────────────────────────────────────────
COSMOS_CONNECTION_STRING: str = os.getenv("COSMOS_CONNECTION_STRING", "")
COSMOS_DATABASE: str = os.getenv("COSMOS_DATABASE", "so-gpt-db")
COSMOS_CONTAINER: str = os.getenv("COSMOS_CONTAINER", "sessions")

# ── Azure Blob Storage ────────────────────────────────────────────────────────
BLOB_CONNECTION_STRING: str = os.getenv("BLOB_CONNECTION_STRING", "")
BLOB_CONTAINER_NAME: str = os.getenv("BLOB_CONTAINER_NAME", "documents")

# ── Azure Document Intelligence ───────────────────────────────────────────────
DOCINTEL_ENDPOINT: str = os.getenv("DOCINTEL_ENDPOINT", "")
DOCINTEL_API_KEY: str = os.getenv("DOCINTEL_API_KEY", "")

# ── Bing Web Search (optional fallback) ──────────────────────────────────────
BING_API_KEY: str = os.getenv("BING_API_KEY", "")
BING_ENDPOINT: str = "https://api.bing.microsoft.com/v7.0/search"

# ── Backend API Key (validated on every /chat request) ───────────────────────
BACKEND_API_KEY: str = os.getenv("BACKEND_API_KEY", "")

# ── Retrieval tuning ──────────────────────────────────────────────────────────
TOP_N_CHUNKS: int = int(os.getenv("TOP_N_CHUNKS", "5"))
RELEVANCE_THRESHOLD: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.75"))
SESSION_HISTORY_TURNS: int = int(os.getenv("SESSION_HISTORY_TURNS", "6"))


def service_status() -> dict[str, bool]:
    """Returns which Azure services are configured — used by /health endpoint."""
    return {
        "openai": bool(OPENAI_ENDPOINT and OPENAI_API_KEY),
        "search": bool(SEARCH_ENDPOINT and SEARCH_API_KEY),
        "cosmos": bool(COSMOS_CONNECTION_STRING),  # required
        "blob": bool(BLOB_CONNECTION_STRING),
        "document_intelligence": bool(DOCINTEL_ENDPOINT and DOCINTEL_API_KEY),
        "bing": bool(BING_API_KEY),
    }
