variable "environment" {
  type        = string
  description = "Environment name (dev, staging, prod)"
  default     = "dev"
}

variable "location" {
  type        = string
  description = "Azure region for all resources"
  default     = "eastus"
}

variable "project_name" {
  type        = string
  description = "Prefix for project resources"
  default     = "forgeops"
}

variable "aks_node_count" {
  type        = number
  description = "Number of worker nodes for the default node pool"
  default     = 2
}

variable "aks_vm_size" {
  type        = string
  description = "VM SKU for the worker nodes"
  default     = "Standard_B2s" # Cost-effective burstable SKU for learning
}
