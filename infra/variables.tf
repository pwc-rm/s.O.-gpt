variable "subscription_id" {
  description = "Azure Subscription ID — find at: Azure Portal → Subscriptions"
  type        = string
}

variable "resource_group_name" {
  description = "Existing resource group (Owner role required)"
  type        = string
  default     = "RG-PLAYGROUND"
}

variable "location" {
  description = "Primary Azure region for all resources"
  type        = string
  default     = "germanywestcentral"
}

variable "openai_location" {
  description = "Region for Azure OpenAI — change if GPT-4o quota not yet approved in primary region"
  type        = string
  default     = "germanywestcentral"
}

variable "project_prefix" {
  description = "Short identifier prefixed on all resource names"
  type        = string
  default     = "so-gpt"
}

variable "environment" {
  description = "Deployment stage appended to resource names"
  type        = string
  default     = "showcase"
}

variable "search_index_name" {
  description = "AI Search index name — must match SEARCH_INDEX_NAME in .env"
  type        = string
  default     = "so-gpt-index"
}

variable "cosmos_database" {
  description = "Cosmos DB SQL database name"
  type        = string
  default     = "so-gpt-db"
}

variable "cosmos_container" {
  description = "Cosmos DB SQL container name for chat sessions"
  type        = string
  default     = "sessions"
}

variable "chat_deployment_name" {
  description = "Name for the GPT-4o model deployment"
  type        = string
  default     = "gpt-4o-deployment"
}

variable "embedding_deployment_name" {
  description = "Name for the text-embedding-3-large deployment"
  type        = string
  default     = "embedding-deployment"
}

variable "query_rewrite_deployment_name" {
  description = "Name for the GPT-4o-mini deployment used for query rewriting (~5x faster, -97% cost vs GPT-4o)"
  type        = string
  default     = "gpt-4o-mini-deployment"
}

variable "gpt4o_capacity" {
  description = "TPM capacity for GPT-4o in thousands (subject to PwC EA quota)"
  type        = number
  default     = 10
}

variable "embedding_capacity" {
  description = "TPM capacity for text-embedding-3-large in thousands"
  type        = number
  default     = 10
}

variable "app_service_sku" {
  description = "App Service Plan SKU — B1 for showcase, P1v3 for production"
  type        = string
  default     = "B1"
}

variable "deployer_ip" {
  description = "Public IP of the machine running terraform apply — added to Key Vault firewall so secrets can be written. Find with: curl -s https://api.ipify.org"
  type        = string
}

variable "create_bing_search" {
  description = "Provision Bing Search via Terraform. Set false if it needs manual Azure Marketplace creation."
  type        = bool
  default     = true
}
