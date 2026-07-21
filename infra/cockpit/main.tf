###############################################################################
# s.Oliver Agent Cockpit — additive Terraform
#
# Referenziert die bestehende s.O-GPT-Sandbox als data sources und legt NUR das
# Neue an: eine eigene Cosmos-DB (agent-cockpit-db) + die Cockpit-Web-App + RBAC.
# Rajs Live-App, sein Image und seine so-gpt-db werden NICHT angefasst.
###############################################################################

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id
  features {}
}

# ── Bestehendes referenzieren (nicht anlegen) ────────────────────────────────
data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

data "azurerm_cosmosdb_account" "cosmos" {
  name                = var.cosmos_account_name
  resource_group_name = var.resource_group_name
}

data "azurerm_key_vault" "kv" {
  name                = var.key_vault_name
  resource_group_name = var.resource_group_name
}

data "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = var.resource_group_name
}

# Geteilter Compute-Plan der s.O-GPT-Test-Instanz (Entscheidung Mike)
data "azurerm_service_plan" "shared" {
  name                = var.app_service_plan_name
  resource_group_name = var.resource_group_name
}

# ── NEU: eigene Cockpit-Datenbank (getrennt von Rajs so-gpt-db) ──────────────
resource "azurerm_cosmosdb_sql_database" "cockpit" {
  name                = "agent-cockpit-db"
  resource_group_name = var.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.cosmos.name
}

resource "azurerm_cosmosdb_sql_container" "agents" {
  name                = "agents"
  resource_group_name = var.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.cosmos.name
  database_name       = azurerm_cosmosdb_sql_database.cockpit.name
  partition_key_paths = ["/category"]
}

resource "azurerm_cosmosdb_sql_container" "agent_chat" {
  name                = "agent_chat"
  resource_group_name = var.resource_group_name
  account_name        = data.azurerm_cosmosdb_account.cosmos.name
  database_name       = azurerm_cosmosdb_sql_database.cockpit.name
  partition_key_paths = ["/agent_id"]
}

# ── NEU: Cockpit Web App (Container aus ACR, eigene App/URL) ──────────────────
resource "azurerm_linux_web_app" "cockpit" {
  name                = var.cockpit_app_name
  resource_group_name = var.resource_group_name
  location            = data.azurerm_resource_group.rg.location
  service_plan_id     = data.azurerm_service_plan.shared.id
  https_only          = true # PwC-Policy az-006 (Pflicht)

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      docker_image_name   = "agent-cockpit:${var.image_tag}"
      docker_registry_url = "https://${data.azurerm_container_registry.acr.login_server}"
    }
    container_registry_use_managed_identity = true
  }

  # config.py lädt Secrets (openai-*, cosmos-connection-string) via Managed
  # Identity aus dem Key Vault. Datenbank/Container-Namen kommen als App-Settings.
  app_settings = {
    AZURE_KEYVAULT_URL         = data.azurerm_key_vault.kv.vault_uri
    WEBSITES_PORT              = "8000"
    COSMOS_DATABASE            = azurerm_cosmosdb_sql_database.cockpit.name
    COSMOS_AGENTS_CONTAINER    = "agents"
    COSMOS_AGENTCHAT_CONTAINER = "agent_chat"
    SOGPT_URL                  = var.sogpt_url
  }

  tags = {
    project    = "agent-cockpit"
    managed_by = "terraform"
  }
}

# ── RBAC für die Managed Identity ────────────────────────────────────────────
resource "azurerm_role_assignment" "acr_pull" {
  scope                = data.azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_web_app.cockpit.identity[0].principal_id
}

resource "azurerm_role_assignment" "kv_reader" {
  scope                = data.azurerm_key_vault.kv.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.cockpit.identity[0].principal_id
}
