variable "subscription_id" {
  description = "Azure Subscription (PZI-DE-E-SUB001)"
  type        = string
  default     = "4155cf68-c489-4a41-be81-ef83a86f8a28"
}

variable "resource_group_name" {
  type    = string
  default = "RG-PLAYGROUND"
}

variable "cosmos_account_name" {
  type    = string
  default = "cosmos-so-gpt-showcase"
}

variable "key_vault_name" {
  type    = string
  default = "kv-so-gpt-showcase"
}

variable "acr_name" {
  type    = string
  default = "sogptshowcase"
}

variable "app_service_plan_name" {
  description = "Geteilter Compute-Plan der s.O-GPT-Test-Instanz"
  type        = string
  default     = "plan-so-gpt-showcase-test"
}

variable "cockpit_app_name" {
  type    = string
  default = "app-agent-cockpit"
}

variable "image_tag" {
  type    = string
  default = "poc"
}

variable "sogpt_url" {
  description = "Ziel des 'Zurück zu s.O GPT'-Links"
  type        = string
  default     = "https://app-so-gpt-showcase-backend-test.azurewebsites.net"
}
