import os
from dotenv import load_dotenv

load_dotenv()

# ── Key Vault (Azure only) ────────────────────────────────────────────────────
# When AZURE_KEYVAULT_URL is set (App Service env var), secrets are loaded from
# Key Vault via Managed Identity at startup. Locally, .env is used as usual.
_KV_SECRETS: dict[str, str] = {}

_kv_url = os.getenv("AZURE_KEYVAULT_URL", "")
if _kv_url:
    from azure.identity import ManagedIdentityCredential
    from azure.keyvault.secrets import SecretClient

    _client = SecretClient(vault_url=_kv_url, credential=ManagedIdentityCredential())

    _SECRET_NAMES = [
        "openai-api-key",
        "openai-endpoint",
        "search-api-key",
        "cosmos-connection-string",
        "blob-connection-string",
        "docintel-api-key",
        "backend-api-key",
        "bing-api-key",
    ]
    for _name in _SECRET_NAMES:
        try:
            _KV_SECRETS[_name] = _client.get_secret(_name).value or ""
        except Exception:
            _KV_SECRETS[_name] = ""


def _get(env_var: str, kv_name: str, default: str = "") -> str:
    """Return KV secret if running in Azure, else fall back to env / default."""
    if _KV_SECRETS:
        return _KV_SECRETS.get(kv_name, default)
    return os.getenv(env_var, default)


# ── Azure OpenAI ──────────────────────────────────────────────────────────────
OPENAI_ENDPOINT: str = _get("OPENAI_ENDPOINT", "openai-endpoint")
OPENAI_API_KEY: str = _get("OPENAI_API_KEY", "openai-api-key")
OPENAI_CHAT_DEPLOYMENT: str = os.getenv("OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
OPENAI_EMBEDDING_DEPLOYMENT: str = os.getenv("OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large")
OPENAI_QUERY_REWRITE_DEPLOYMENT: str = os.getenv("OPENAI_QUERY_REWRITE_DEPLOYMENT", "gpt-4.1-mini")
OPENAI_API_VERSION: str = os.getenv("OPENAI_API_VERSION", "2024-08-01-preview")

# ── Azure AI Search ───────────────────────────────────────────────────────────
SEARCH_ENDPOINT: str = os.getenv("SEARCH_ENDPOINT", "")
SEARCH_API_KEY: str = _get("SEARCH_API_KEY", "search-api-key")
SEARCH_INDEX_NAME: str = os.getenv("SEARCH_INDEX_NAME", "so-gpt-index")
SEARCH_SEMANTIC_CONFIG: str = "default"

# ── Azure Cosmos DB (Session Store) ──────────────────────────────────────────
COSMOS_CONNECTION_STRING: str = _get("COSMOS_CONNECTION_STRING", "cosmos-connection-string")
COSMOS_DATABASE: str = os.getenv("COSMOS_DATABASE", "so-gpt-db")
COSMOS_CONTAINER: str = os.getenv("COSMOS_CONTAINER", "sessions")

# ── Azure Blob Storage ────────────────────────────────────────────────────────
BLOB_CONNECTION_STRING: str = _get("BLOB_CONNECTION_STRING", "blob-connection-string")
BLOB_CONTAINER_NAME: str = os.getenv("BLOB_CONTAINER_NAME", "documents")

# ── Azure Document Intelligence ───────────────────────────────────────────────
DOCINTEL_ENDPOINT: str = os.getenv("DOCINTEL_ENDPOINT", "")
DOCINTEL_API_KEY: str = _get("DOCINTEL_API_KEY", "docintel-api-key")

# ── Bing Web Search (optional fallback) ──────────────────────────────────────
BING_API_KEY: str = _get("BING_API_KEY", "bing-api-key")
BING_ENDPOINT: str = "https://api.bing.microsoft.com/v7.0/search"

# ── Backend API Key (validated on every /chat request) ───────────────────────
BACKEND_API_KEY: str = _get("BACKEND_API_KEY", "backend-api-key")

# ── Retrieval tuning ──────────────────────────────────────────────────────────
TOP_N_CHUNKS: int = int(os.getenv("TOP_N_CHUNKS", "5"))
RELEVANCE_THRESHOLD: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.75"))
SESSION_HISTORY_TURNS: int = int(os.getenv("SESSION_HISTORY_TURNS", "6"))


def service_status() -> dict[str, bool]:
    """Returns which Azure services are configured — used by /health endpoint."""
    return {
        "openai": bool(OPENAI_ENDPOINT and OPENAI_API_KEY),
        "search": bool(SEARCH_ENDPOINT and SEARCH_API_KEY),
        "cosmos": bool(COSMOS_CONNECTION_STRING),
        "blob": bool(BLOB_CONNECTION_STRING),
        "document_intelligence": bool(DOCINTEL_ENDPOINT and DOCINTEL_API_KEY),
        "bing": bool(BING_API_KEY),
    }
