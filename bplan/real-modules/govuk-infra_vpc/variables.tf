variable "govuk_environment" {
  type        = string
  description = "GOV.UK environment where resources are being deployed"
  default     = "govuk_environment"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "eu-west-1"
}

variable "vpc_cidr" {
  type        = string
  description = "VPC IP address range, represented as a CIDR block"
  default     = "10.0.0.0/17" # trigger change
}

variable "traffic_type" {
  type        = string
  description = "The traffic type to capture. Allows ACCEPT, ALL or REJECT"
  default     = "REJECT"
}

variable "cluster_log_retention_in_days" {
  type        = string
  description = "Number of days to retain Cloudwatch logs for"
  default     = "n days"
}

variable "cyber_slunk_s3_bucket_name" {
  type        = string
  description = "Bucket to store logs for ingestion by Splunk"
  default     = "central-pipeline-logging-prod-non-cw"
}

variable "cyber_slunk_aws_account_id" {
  type        = string
  description = "Account ID which holds the Splunk log bucket"
  default     = "885513274347"
}

variable "legacy_private_subnets" {
  type        = map(object({ az = string, cidr = string, nat = bool }))
  description = "Map of {subnet_name: {az=<az>, cidr=<cidr>}} for the private subnets for legacy resources"
  default     = {
    subnet1 = {
      az = "eu-west-1c"
      cidr = "10.0.1.0/24"
      nat = false
    }
    # subnet2 = {
    #   az = "az2"
    #   cidr = "192.168.0.0/24"
    #   nat = true
    # }
  }
}

variable "legacy_public_subnets" {
  type        = map(object({ az = string, cidr = string }))
  description = "Map of {subnet_name: {az=<az>, cidr=<cidr>}} for the public subnets for legacy resources"
  default     = {
    subnet1 = {
      az = "eu-west-1c"
      cidr = "10.0.2.0/24"
    }
    # subnet2 = {
    #   az = "az2"
    #   cidr = "192.168.0.0/24"
    # }
  }
}
