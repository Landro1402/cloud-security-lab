terraform {
  required_version = ">= 1.5, < 2.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0, < 7.0"
    }
  }
}

variable "aws_profile" {
  description = "Local AWS profile used to authenticate"
  type        = string
}

variable "expected_account_id" {
  description = "AWS account allowed for this lab"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "The AWS account ID must contain 12 digits."
  }
}

variable "bucket_prefix" {
  description = "Prefix used to generate the lab bucket name"
  type        = string
  default     = "cloud-security-lab-"
}

provider "aws" {
  region              = "eu-north-1"
  profile             = var.aws_profile
  allowed_account_ids = [var.expected_account_id]

  default_tags {
    tags = {
      Project   = "cloud-security-lab"
      ManagedBy = "Terraform"
    }
  }
}

data "aws_caller_identity" "current" {}

output "authenticated_account" {
  description = "AWS account used by Terraform"
  value       = data.aws_caller_identity.current.account_id
}
