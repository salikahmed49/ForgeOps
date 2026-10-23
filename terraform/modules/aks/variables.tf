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
  description = "Prefix for naming resources"
}

variable "subnet_id" {
  type        = string
  description = "Subnet ID for the AKS default node pool"
}

variable "node_count" {
  type        = number
  description = "Initial number of nodes"
  default     = 2
}

variable "vm_size" {
  type        = string
  description = "VM SKU for the worker nodes"
  default     = "Standard_B2s"
}

variable "acr_id" {
  type        = string
  description = "Azure Container Registry ID for AcrPull role assignment"
}

variable "tags" {
  type        = map(string)
  description = "Tags to attach to resources"
  default     = {}
}
