variable "my_ip" {
  description = "Your public IP address for SSH access (format: x.x.x.x/32)"
  type        = string
  sensitive   = true
}

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "eu-west-2"
}

variable "key_pair_name" {
  description = "Name of the AWS EC2 key pair for SSH access"
  type        = string
}

variable "project_name" {
  description = "Name of the project for resource naming and tagging"
  type        = string
  default     = "discord-bot"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}