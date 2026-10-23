output "resource_group_name" {
  value       = azurerm_resource_group.rg.name
  description = "Name of the created Resource Group"
}

output "acr_login_server" {
  value       = module.acr.login_server
  description = "Login server endpoint for docker push"
}

output "acr_name" {
  value       = module.acr.acr_name
  description = "Name of the Azure Container Registry"
}

output "aks_cluster_name" {
  value       = module.aks.cluster_name
  description = "Name of the AKS cluster"
}

output "get_credentials_command" {
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.rg.name} --name ${module.aks.cluster_name}"
  description = "Command to configure kubectl to point to this Azure AKS cluster"
}
