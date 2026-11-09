output "instance_id" {
  description = "New EC2 instance ID."
  value       = aws_instance.mcp.id
}

output "public_ip" {
  description = "Public IP of the new instance."
  value       = aws_instance.mcp.public_ip
}

output "private_ip" {
  description = "Private IP of the new instance."
  value       = aws_instance.mcp.private_ip
}

output "ami_id" {
  description = "AMI reused from the reference instance (Amazon Linux 2023)."
  value       = aws_instance.mcp.ami
}

output "instance_type" {
  description = "Instance type that was launched."
  value       = aws_instance.mcp.instance_type
}

locals {
  ssh_key_arg = var.ssh_private_key_path == "" ? "" : "-i ${var.ssh_private_key_path} "
}

output "ssh_command" {
  description = "SSH into the new instance."
  value       = "ssh ${local.ssh_key_arg}ec2-user@${aws_instance.mcp.public_ip}"
}

output "ssh_tunnel_command" {
  description = "Forward local 8080 to the client container on the instance."
  value       = "ssh ${local.ssh_key_arg}-N -L ${var.mcp_port}:127.0.0.1:${var.mcp_port} ec2-user@${aws_instance.mcp.public_ip}"
}

output "app_local_url" {
  description = "Client API base URL while the SSH tunnel is running (UI uses /chat, /health, /tools)."
  value       = "http://localhost:${var.mcp_port}"
}

output "app_public_url" {
  description = "Direct URL, only when mcp_ingress_cidrs is non-empty. Prefer TLS in front."
  value       = length(var.mcp_ingress_cidrs) > 0 ? "http://${aws_instance.mcp.public_ip}:${var.mcp_port}" : null
}

# Kept for backwards compatibility with older tooling.
output "mcp_local_url" {
  description = "Alias of app_local_url."
  value       = "http://localhost:${var.mcp_port}"
}

output "mcp_public_url" {
  description = "Alias of app_public_url."
  value       = length(var.mcp_ingress_cidrs) > 0 ? "http://${aws_instance.mcp.public_ip}:${var.mcp_port}" : null
}
