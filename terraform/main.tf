locals {
  name_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Project     = "ForgeOps"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.name_prefix}"
  location = var.location
  tags     = local.common_tags
}

module "networking" {
  source              = "./modules/networking"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  name_prefix         = local.name_prefix
  tags                = local.common_tags
}

module "acr" {
  source              = "./modules/acr"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  name_prefix         = replace(local.name_prefix, "-", "") # ACR names must be alphanumeric
  tags                = local.common_tags
}

module "aks" {
  source              = "./modules/aks"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  name_prefix         = local.name_prefix
  subnet_id           = module.networking.aks_subnet_id
  node_count          = var.aks_node_count
  vm_size             = var.aks_vm_size
  acr_id              = module.acr.acr_id
  tags                = local.common_tags
}
