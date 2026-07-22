terraform {
  # cloud {
  #   organization = "govuk"
  #   workspaces {
  #     tags = ["vpc", "eks", "aws"]
  #   }
  # }
  required_version = "~> 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "eu-west-1"
  # skip_requesting_account_id  = true
  # skip_credentials_validation = true
  # skip_metadata_api_check     = true
  # skip_region_validation      = true
  # access_key                  = "mock_access_key"
  # secret_key                  = "mock_secret_key"
  # profile                     = "default"   # maybe set a dummy shared profile ?
  default_tags {
    tags = {
      Product              = "GOV.UK"
      System               = "VPC"
      Environment          = var.govuk_environment
      Owner                = "govuk-platform-engineering@digital.cabinet-office.gov.uk"
      repository           = "govuk-infrastructure"
      terraform_deployment = basename(abspath(path.root))
    }
  }
}

locals {
  is_ephemeral = startswith(var.govuk_environment, "eph-")
}
