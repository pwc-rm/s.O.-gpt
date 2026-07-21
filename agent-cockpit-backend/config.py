"""
s.Oliver Agent Cockpit — Configuration

Mirrors the s.O GPT config pattern: when AZURE_KEYVAULT_URL is set (App Service),
secrets are loaded from Key Vault via Managed Identity at startup. Locally, .env
is used. The Cockpit deliberately reuses the SAME Key Vault as the s.O GPT (for the
OpenAI endpoint/key) but writes its data into its OWN Cosmos database
(agent-cockpit-db) — Raj's so-gpt-db is never touched.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Key Vault (Azure only) ────────────────────────────────────────────────────
_KV_SECRETS: dict[str, str] = {}

_kv_url = os.getenv("AZURE_KEYVAULT_URL", "")
if _kv_url:
    from azure.identity import ManagedIdentityCredential
    from azure.keyvault.secrets import SecretClient

    _client = SecretClient(vault_url=_kv_url, credential=ManagedIdentityCredential())

    # Only the secrets the Cockpit needs — read-only, shared with s.O GPT.
    _SECRET_NAMES = [
        "openai-api-key",
        "openai-endpoint",
        "cosmos-connection-string",
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


# ── Azure OpenAI (shared endpoint with s.O GPT — real agent chat) ─────────────
OPENAI_ENDPOINT: str = _get("OPENAI_ENDPOINT", "openai-endpoint")
OPENAI_API_KEY: str = _get("OPENAI_API_KEY", "openai-api-key")
OPENAI_CHAT_DEPLOYMENT: str = os.getenv("OPENAI_CHAT_DEPLOYMENT", "gpt-4o")
OPENAI_API_VERSION: str = os.getenv("OPENAI_API_VERSION", "2024-08-01-preview")

# ── Cosmos DB (OWN database — isolated from Raj's so-gpt-db) ───────────────────
COSMOS_CONNECTION_STRING: str = _get("COSMOS_CONNECTION_STRING", "cosmos-connection-string")
COSMOS_DATABASE: str = os.getenv("COSMOS_DATABASE", "agent-cockpit-db")
COSMOS_AGENTS_CONTAINER: str = os.getenv("COSMOS_AGENTS_CONTAINER", "agents")
COSMOS_AGENTCHAT_CONTAINER: str = os.getenv("COSMOS_AGENTCHAT_CONTAINER", "agent_chat")

# ── Link back to the s.O GPT ("Zurück zu s.O GPT") ────────────────────────────
SOGPT_URL: str = os.getenv("SOGPT_URL", "https://app-so-gpt-showcase-backend-test.azurewebsites.net")


def service_status() -> dict[str, bool]:
    """Returns which backing services are configured — used by /health."""
    return {
        "openai": bool(OPENAI_ENDPOINT and OPENAI_API_KEY),
        "cosmos": bool(COSMOS_CONNECTION_STRING),
    }
