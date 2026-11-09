terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# The source of truth for OS/AMI, key pair and subnet. The new instance uses
# the same Amazon Linux 2023 AMI as this reference instance.
data "aws_instance" "reference" {
  instance_id = var.reference_instance_id
}

data "aws_subnet" "target" {
  id = coalesce(var.subnet_id, data.aws_instance.reference.subnet_id)
}

# Optional public MCP ingress. Left disabled by default: the recommended setup
# is to reach the server through an SSH tunnel, so only port 22 from the
# existing SSH security group is exposed.
resource "aws_security_group" "mcp" {
  count       = length(var.mcp_ingress_cidrs) > 0 ? 1 : 0
  name        = "${var.project_name}-mcp"
  description = "MCP HTTP access for ${var.project_name}"
  vpc_id      = data.aws_subnet.target.vpc_id

  ingress {
    description = "MCP streamable HTTP"
    from_port   = var.mcp_port
    to_port     = var.mcp_port
    protocol    = "tcp"
    cidr_blocks = var.mcp_ingress_cidrs
  }

  egress {
    description = "Outbound for image pulls and the IAM API"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-mcp"
  }
}

resource "aws_instance" "mcp" {
  ami                         = data.aws_instance.reference.ami
  instance_type               = var.instance_type
  key_name                    = coalesce(var.key_name, data.aws_instance.reference.key_name)
  subnet_id                   = data.aws_subnet.target.id
  vpc_security_group_ids      = compact(concat([var.ssh_security_group_id, var.mcp_security_group_id], aws_security_group.mcp[*].id))
  associate_public_ip_address = true
  iam_instance_profile        = var.iam_instance_profile

  user_data = file("${path.module}/user_data.sh")

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  tags = {
    Name = var.instance_name
  }

  lifecycle {
    # The live instance already has Docker installed and was launched outside
    # Terraform; do not replace it just because user_data differs.
    ignore_changes = [user_data]
  }
}
