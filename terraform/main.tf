terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
  }

  required_version = ">= 1.2.0"
}

provider "aws" {
  region = var.aws_region
}

resource "aws_key_pair" "discord_bot" {
  key_name   = var.key_pair_name
  public_key = file("~/.ssh/id_rsa.pub")

  tags = {
    Name        = "${var.project_name}-${var.environment}-key"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_instance" "discord_bot" {
  ami                    = "ami-0532f1280ac457a8f"
  instance_type          = var.instance_type
  key_name               = aws_key_pair.discord_bot.key_name
  vpc_security_group_ids = [aws_security_group.ssh.id]

  tags = {
    Name        = "${var.project_name}-${var.environment}"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_security_group" "ssh" {
  name        = "${var.project_name}-${var.environment}-ssh"
  description = "Allow SSH access for ${var.project_name}"

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ssh"
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

output "public_ip" {
  value = aws_instance.discord_bot.public_ip
}