terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
  }

  # For initial local testing, this backend block can remain commented out.
  # Once you bootstrap your Azure Storage Account (Step 3.2 in docs/phase-2-terraform-azure-iac.md),
  # uncomment this block and fill in your storage_account_name.
  #
  # backend "azurerm" {
  #   resource_group_name  = "rg-forgeops-tfstate"
  #   storage_account_name = "REPLACE_WITH_YOUR_STORAGE_ACCOUNT"
  #   container_name       = "tfstate"
  #   key                  = "forgeops.dev.terraform.tfstate"
  # }
}

provider "azurerm" {
  features {}
}
