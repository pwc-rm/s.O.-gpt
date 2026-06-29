terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = false
    }
    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
  }
}

data "azurerm_client_config" "current" {}

# Reference the existing resource group — do not create a new one.
data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

locals {
  suffix    = "${var.project_prefix}-${var.environment}"    # so-gpt-showcase
  safe_name = replace("${var.project_prefix}${var.environment}", "-", "")  # sogptshowcase
  tags = {
    project     = var.project_prefix
    environment = var.environment
    managed_by  = "terraform"
  }
}

# ── Blob Storage (document corpus) ────────────────────────────────────────────

resource "azurerm_storage_account" "docs" {
  name                     = "st${local.safe_name}"
  resource_group_name      = data.azurerm_resource_group.rg.name
  location                 = data.azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  tags                     = local.tags
}

resource "azurerm_storage_container" "documents" {
  name                  = "documents"
  storage_account_id    = azurerm_storage_account.docs.id
  container_access_type = "private"
}

# ── Document Intelligence (PDF extraction + OCR) ──────────────────────────────

resource "azurerm_cognitive_account" "docintel" {
  name                = "docintel-${local.suffix}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  kind                = "FormRecognizer"
  sku_name            = "S0"
  tags                = local.tags
}

# ── Azure AI Search (vector + BM25 hybrid + semantic ranking) ─────────────────

resource "azurerm_search_service" "search" {
  name                = "srch-${local.suffix}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  sku                 = "basic"
  semantic_search_sku = "free"  # enables semantic ranking (1 000 queries/month included)
  tags                = local.tags
}

# ── Cosmos DB (chat session store) ────────────────────────────────────────────

resource "azurerm_cosmosdb_account" "sessions" {
  name                = "cosmos-${local.suffix}"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = data.azurerm_resource_group.rg.location
    failover_priority = 0
  }

  capabilities {
    name = "EnableServerless"
  }

  tags = local.tags
}

resource "azurerm_cosmosdb_sql_database" "db" {
  name                = var.cosmos_database
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.sessions.name
}

resource "azurerm_cosmosdb_sql_container" "sessions" {
  name                = var.cosmos_container
  resource_group_name = data.azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.sessions.name
  database_name       = azurerm_cosmosdb_sql_database.db.name
  partition_key_paths = ["/session_id"]
}

# ── Azure OpenAI ──────────────────────────────────────────────────────────────
# NOTE: PwC policy az-005 blocks direct OpenAI resource creation.
# OpenAI endpoint + key must be obtained from PwC GHS (pwc.to/generative-ai)
# and set manually in Key Vault after deployment:
#   az keyvault secret set --vault-name kv-so-gpt-showcase --name openai-endpoint --value "https://..."
#   az keyvault secret set --vault-name kv-so-gpt-showcase --name openai-api-key --value "..."

# ── Bing Search (optional web fallback) ───────────────────────────────────────
# If this fails: set create_bing_search=false and provision manually in Azure Marketplace,
# then update the bing-api-key secret in Key Vault.

resource "azurerm_cognitive_account" "bing" {
  count               = var.create_bing_search ? 1 : 0
  name                = "bing-${local.suffix}"
  location            = "global"
  resource_group_name = data.azurerm_resource_group.rg.name
  kind                = "Bing.Search.v7"
  sku_name            = "S1"
  tags                = local.tags
}

# ── Key Vault (RBAC model) ────────────────────────────────────────────────────
# All secrets are written here by Terraform. App Service reads them via
# Key Vault References (@Microsoft.KeyVault(...)) — no SDK changes in config.py.

resource "azurerm_key_vault" "kv" {
  name                      = "kv-${local.suffix}"
  location                  = data.azurerm_resource_group.rg.location
  resource_group_name       = data.azurerm_resource_group.rg.name
  tenant_id                 = data.azurerm_client_config.current.tenant_id
  sku_name                  = "standard"
  rbac_authorization_enabled = true

  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
    ip_rules       = [var.deployer_ip]
  }

  tags = local.tags
}

# Current user (running terraform apply) — can create/update secrets
resource "azurerm_role_assignment" "kv_admin" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# App Service Managed Identity — read-only on secrets
resource "azurerm_role_assignment" "kv_app_reader" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.backend.identity[0].principal_id
}

# ── Key Vault Secrets ─────────────────────────────────────────────────────────

resource "random_password" "backend_api_key" {
  length  = 64
  special = false
}

resource "azurerm_key_vault_secret" "openai_endpoint" {
  name         = "openai-endpoint"
  value        = "PLACEHOLDER_SET_MANUALLY"
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "openai_api_key" {
  name         = "openai-api-key"
  value        = "PLACEHOLDER_SET_MANUALLY"
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "search_endpoint" {
  name         = "search-endpoint"
  value        = "https://${azurerm_search_service.search.name}.search.windows.net"
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "search_api_key" {
  name         = "search-api-key"
  value        = azurerm_search_service.search.primary_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "cosmos_connection_string" {
  name         = "cosmos-connection-string"
  value        = azurerm_cosmosdb_account.sessions.primary_sql_connection_string
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "blob_connection_string" {
  name         = "blob-connection-string"
  value        = azurerm_storage_account.docs.primary_connection_string
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "docintel_endpoint" {
  name         = "docintel-endpoint"
  value        = azurerm_cognitive_account.docintel.endpoint
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "docintel_api_key" {
  name         = "docintel-api-key"
  value        = azurerm_cognitive_account.docintel.primary_access_key
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "bing_api_key" {
  name  = "bing-api-key"
  value = try(azurerm_cognitive_account.bing[0].primary_access_key, "PLACEHOLDER_SET_MANUALLY")
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "backend_api_key" {
  name         = "backend-api-key"
  value        = random_password.backend_api_key.result
  key_vault_id = azurerm_key_vault.kv.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

# ── Azure Function App (event-driven ingestion) ───────────────────────────────
# Fires automatically when a document lands in the 'documents' Blob container.
# Consumption plan (Y1) = serverless, billed per execution, free for low volume.

resource "azurerm_service_plan" "func" {
  name                = "plan-${local.suffix}-func"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1"
  tags                = local.tags
}

resource "azurerm_linux_function_app" "ingest" {
  name                          = "func-${local.suffix}-ingest"
  resource_group_name           = data.azurerm_resource_group.rg.name
  location                      = data.azurerm_resource_group.rg.location
  service_plan_id               = azurerm_service_plan.func.id
  storage_account_name          = azurerm_storage_account.docs.name
  storage_uses_managed_identity = true
  https_only                    = true

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  # BLOB_CONNECTION_STRING is the trigger connection — the Functions runtime
  # resolves the Key Vault reference before listening for blob events.
  app_settings = {
    FUNCTIONS_WORKER_RUNTIME        = "python"
    BLOB_CONNECTION_STRING          = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.blob_connection_string.versionless_id})"
    BLOB_CONTAINER_NAME             = "documents"
    OPENAI_ENDPOINT                 = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_endpoint.versionless_id})"
    OPENAI_API_KEY                  = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_api_key.versionless_id})"
    OPENAI_EMBEDDING_DEPLOYMENT     = var.embedding_deployment_name
    SEARCH_ENDPOINT                 = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.search_endpoint.versionless_id})"
    SEARCH_API_KEY                  = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.search_api_key.versionless_id})"
    SEARCH_INDEX_NAME               = var.search_index_name
    DOCINTEL_ENDPOINT               = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.docintel_endpoint.versionless_id})"
    DOCINTEL_API_KEY                = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.docintel_api_key.versionless_id})"
    SCM_DO_BUILD_DURING_DEPLOYMENT  = "true"
  }

  tags = local.tags
}

# Function App Managed Identity → Key Vault (read secrets)
resource "azurerm_role_assignment" "kv_func_reader" {
  scope                = azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_function_app.ingest.identity[0].principal_id
}

# Function App Managed Identity → Blob Storage (read blobs + manage Function state)
resource "azurerm_role_assignment" "func_storage_owner" {
  scope                = azurerm_storage_account.docs.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = azurerm_linux_function_app.ingest.identity[0].principal_id
}

# ── App Service Plan + Web App ────────────────────────────────────────────────

resource "azurerm_service_plan" "backend" {
  name                = "plan-${local.suffix}"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = var.app_service_sku
  tags                = local.tags
}

resource "azurerm_linux_web_app" "backend" {
  name                = "app-${local.suffix}-backend"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  service_plan_id     = azurerm_service_plan.backend.id
  https_only          = true

  # System-Assigned Managed Identity — used to read secrets from Key Vault.
  # The kv_app_reader role assignment below grants it Key Vault Secrets User.
  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
    app_command_line = "uvicorn main:app --host 0.0.0.0 --port 8000"
  }

  # App Service Key Vault References: Azure resolves @Microsoft.KeyVault(...)
  # at runtime via the Managed Identity. config.py reads os.getenv() unchanged.
  app_settings = {
    OPENAI_ENDPOINT             = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_endpoint.versionless_id})"
    OPENAI_API_KEY              = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.openai_api_key.versionless_id})"
    OPENAI_CHAT_DEPLOYMENT            = var.chat_deployment_name
    OPENAI_EMBEDDING_DEPLOYMENT       = var.embedding_deployment_name
    OPENAI_QUERY_REWRITE_DEPLOYMENT   = var.query_rewrite_deployment_name
    SEARCH_ENDPOINT             = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.search_endpoint.versionless_id})"
    SEARCH_API_KEY              = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.search_api_key.versionless_id})"
    SEARCH_INDEX_NAME           = var.search_index_name
    COSMOS_CONNECTION_STRING    = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.cosmos_connection_string.versionless_id})"
    COSMOS_DATABASE             = var.cosmos_database
    COSMOS_CONTAINER            = var.cosmos_container
    BLOB_CONNECTION_STRING      = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.blob_connection_string.versionless_id})"
    BLOB_CONTAINER_NAME         = "documents"
    DOCINTEL_ENDPOINT           = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.docintel_endpoint.versionless_id})"
    DOCINTEL_API_KEY            = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.docintel_api_key.versionless_id})"
    BING_API_KEY                = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.bing_api_key.versionless_id})"
    BACKEND_API_KEY             = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.backend_api_key.versionless_id})"
    TOP_N_CHUNKS                = "5"
    RELEVANCE_THRESHOLD         = "0.75"
    SESSION_HISTORY_TURNS       = "6"
    SCM_DO_BUILD_DURING_DEPLOYMENT = "true"
  }

  tags = local.tags
}
