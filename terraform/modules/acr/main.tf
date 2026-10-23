resource "azurerm_container_registry" "acr" {
  name                = "acr${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku
  admin_enabled       = false # Security hardening: rely on Azure Active Directory and Managed Identity
  tags                = var.tags
}
