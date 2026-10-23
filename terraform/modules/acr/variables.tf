variable "resource_group_name" {
  type        = string
  description = "Name of the parent resource group"
}

variable "location" {
  type        = string
  description = "Azure region"
}

variable "name_prefix" {
  type        = string
  description = "Alphanumeric prefix for naming ACR (no dashes)"
}

variable "sku" {
  type        = string
  description = "ACR pricing tier (Basic, Standard, Premium)"
  default     = "Standard"
}

variable "tags" {
  type        = map(string)
  description = "Tags to attach to resources"
  default     = {}
}
