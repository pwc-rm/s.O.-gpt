output "cockpit_url" {
  description = "URL der Agent-Cockpit-App"
  value       = "https://${azurerm_linux_web_app.cockpit.default_hostname}"
}

output "cosmos_database" {
  value = azurerm_cosmosdb_sql_database.cockpit.name
}
