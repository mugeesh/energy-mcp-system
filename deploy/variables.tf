variable "aws_region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project tag and resource prefix."
  type        = string
  default     = "iam-mcp"
}

variable "environment" {
  description = "Environment tag."
  type        = string
  default     = "staging"
}

variable "instance_name" {
  description = "Name tag of the new EC2 instance."
  type        = string
  default     = "iam-mcp"
}

variable "instance_type" {
  description = "Smallest practical general-purpose type for Docker + an MCP server."
  type        = string
  default     = "t3.micro"

  validation {
    condition     = can(regex("^t[23][a-z]?\\.(micro|small|medium)$", var.instance_type))
    error_message = "Use a small burstable type such as t3.micro, t3a.micro or t2.micro."
  }
}

variable "reference_instance_id" {
  description = "Existing instance whose OS/AMI, key pair and subnet are reused."
  type        = string
  default     = "i-0dea36dc6abf6749d"
}

variable "ssh_security_group_id" {
  description = "Existing SSH security group to attach."
  type        = string
  default     = "sg-02e544f5d335d5127"
}

variable "mcp_security_group_id" {
  description = "Existing security group that allows MCP port 8080 (live staging: sg-0585276470a82e032). Set to null to skip attaching it."
  type        = string
  default     = "sg-0585276470a82e032"
}

variable "key_name" {
  description = "EC2 key pair. Null reuses the reference instance's key pair."
  type        = string
  default     = null
}

variable "subnet_id" {
  description = "Subnet. Null reuses the reference instance's subnet (public, us-east-1a)."
  type        = string
  default     = null
}

variable "iam_instance_profile" {
  description = "Optional instance profile, e.g. for ECR pulls. Null attaches none."
  type        = string
  default     = null
}

variable "root_volume_size" {
  description = "Root gp3 volume size in GiB."
  type        = number
  default     = 8
}

variable "mcp_port" {
  description = "Host port for the FastAPI client / UI backend (container listens on 8000)."
  type        = number
  default     = 8080
}

variable "mcp_ingress_cidrs" {
  description = "CIDRs allowed to reach mcp_port publicly. Empty keeps it loopback-only (use an SSH tunnel)."
  type        = list(string)
  default     = []
}

variable "ssh_private_key_path" {
  description = "Optional local private key path used only in the generated SSH output commands. Leave empty when using ssh-agent or EC2 Instance Connect."
  type        = string
  default     = ""
}
