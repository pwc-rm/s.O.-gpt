# ── Public endpoints ──────────────────────────────────────────────────────────

output "app_service_url" {
  description = "Backend URL — set as API_URL in frontend/index.html"
  value       = "https://${azurerm_linux_web_app.backend.default_hostname}"
}

output "openai_endpoint" {
  description = "OPENAI_ENDPOINT — set manually via: az keyvault secret set --vault-name kv-so-gpt-showcase --name openai-endpoint --value <url>"
  value       = "PLACEHOLDER — obtain from PwC GHS (pwc.to/generative-ai) and update Key Vault manually"
}

output "search_endpoint" {
  description = "SEARCH_ENDPOINT for local .env"
  value       = "https://${azurerm_search_service.search.name}.search.windows.net"
}

output "docintel_endpoint" {
  description = "DOCINTEL_ENDPOINT for local .env"
  value       = azurerm_cognitive_account.docintel.endpoint
}

output "key_vault_name" {
  description = "Key Vault where all secrets are stored"
  value       = azurerm_key_vault.kv.name
}

output "storage_account_name" {
  description = "Blob Storage account — upload documents to the 'documents' container here"
  value       = azurerm_storage_account.docs.name
}

output "app_service_name" {
  description = "App Service resource name — used in az webapp deploy commands"
  value       = azurerm_linux_web_app.backend.name
}

output "function_app_name" {
  description = "Function App resource name — used in func azure functionapp publish"
  value       = azurerm_linux_function_app.ingest.name
}

# ── Sensitive outputs ─────────────────────────────────────────────────────────
# Retrieve individual values for .env:
#   terraform output -raw backend_api_key
#   terraform output -raw openai_api_key
# Or dump all to JSON:
#   terraform output -json

output "backend_api_key" {
  description = "Generated BACKEND_API_KEY — paste into .env and frontend/index.html API_KEY"
  value       = random_password.backend_api_key.result
  sensitive   = true
}

output "openai_api_key" {
  description = "OPENAI_API_KEY — set manually via: az keyvault secret set --vault-name kv-so-gpt-showcase --name openai-api-key --value <key>"
  value       = "PLACEHOLDER — obtain from PwC GHS and update Key Vault manually"
  sensitive   = true
}

output "search_api_key" {
  description = "SEARCH_API_KEY for local .env"
  value       = azurerm_search_service.search.primary_key
  sensitive   = true
}

output "cosmos_connection_string" {
  description = "COSMOS_CONNECTION_STRING for local .env"
  value       = azurerm_cosmosdb_account.sessions.primary_sql_connection_string
  sensitive   = true
}

output "blob_connection_string" {
  description = "BLOB_CONNECTION_STRING for local .env"
  value       = azurerm_storage_account.docs.primary_connection_string
  sensitive   = true
}

output "docintel_api_key" {
  description = "DOCINTEL_API_KEY for local .env"
  value       = azurerm_cognitive_account.docintel.primary_access_key
  sensitive   = true
}

output "bing_api_key" {
  description = "BING_API_KEY for local .env (empty if create_bing_search=false)"
  value       = try(azurerm_cognitive_account.bing[0].primary_access_key, "")
  sensitive   = true
}

# ── Next steps ────────────────────────────────────────────────────────────────

output "next_steps" {
  description = "Post-deployment checklist"
  value       = <<-EOT

    ✅  Infrastructure ready. Run in this order:

    1. Populate local .env:
         terraform output -raw openai_endpoint   → OPENAI_ENDPOINT
         terraform output -raw openai_api_key    → OPENAI_API_KEY
         terraform output -raw search_endpoint   → SEARCH_ENDPOINT
         terraform output -raw search_api_key    → SEARCH_API_KEY
         terraform output -raw cosmos_connection_string → COSMOS_CONNECTION_STRING
         terraform output -raw blob_connection_string   → BLOB_CONNECTION_STRING
         terraform output -raw docintel_endpoint → DOCINTEL_ENDPOINT
         terraform output -raw docintel_api_key  → DOCINTEL_API_KEY
         terraform output -raw backend_api_key   → BACKEND_API_KEY

    2. Create the AI Search index:
         cd so-gpt-backend && python create_index.py

    3. Upload documents to Blob Storage (account: ${azurerm_storage_account.docs.name}, container: documents)

    4. Run ingestion pipeline:
         python ingestion.py

    5. Deploy backend:
         cd so-gpt-backend
         zip -r ../deploy.zip . -x "venv/*" "*.pyc" "__pycache__/*"
         az webapp deploy --resource-group ${data.azurerm_resource_group.rg.name} \
           --name ${azurerm_linux_web_app.backend.name} \
           --src-path ../deploy.zip

    6. Update frontend/index.html:
         API_URL = 'https://${azurerm_linux_web_app.backend.default_hostname}/chat'
         API_KEY = '<terraform output -raw backend_api_key>'
  EOT
}
