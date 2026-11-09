# EC2 deployment for iam-mcp

Terraform for a standalone EC2 instance that runs the `iam-mcp` Docker Compose
stack (MCP server + DeepSeek-powered FastAPI client). It matches the OS, key
pair and network of the reference instance `i-0dea36dc6abf6749d`.

## What gets created

| Item | Value |
| --- | --- |
| Region | `us-east-1` |
| AMI | same Amazon Linux 2023 AMI as `i-0dea36dc6abf6749d` |
| Instance type | `t3.micro` (override with `instance_type`) |
| Subnet | same public subnet as the reference (`us-east-1a`) |
| Security groups | SSH `sg-02e544f5d335d5127` + app port `sg-0585276470a82e032` |
| Storage | 8 GiB gp3, encrypted |
| Software | Docker Engine + compose plugin, git, rsync, 2 GiB swap |
| App port | host `8080` → client container `8000` (MCP server stays on the compose network) |

## Prerequisites

- Terraform >= 1.5 and AWS CLI
- AWS credentials in the environment (SSO or access keys)
- SSH access to the instance

```bash
export AWS_PROFILE=...
cd deploy
cp terraform.tfvars.example terraform.tfvars   # optional overrides
terraform init
terraform plan
terraform apply
```

Outputs include `public_ip`, `instance_id`, `ssh_command`,
`ssh_tunnel_command` and `app_local_url`.

## Deploy the stack

Copy the project (including `docker-compose.yml`, `mcp-server-client/` and
`deploy/`) to `/opt/iam-mcp`:

```bash
IP=$(terraform output -raw public_ip)
tar czf - --exclude .venv --exclude __pycache__ --exclude .env \
  --exclude .git --exclude 'deploy/.terraform*' \
  -C .. . \
  | ssh ec2-user@"$IP" \
      'sudo mkdir -p /opt/iam-mcp && sudo chown ec2-user:ec2-user /opt/iam-mcp && tar xzf - -C /opt/iam-mcp'
```

On the instance, create `/opt/iam-mcp/.env` from `.env.example` and set at
least `DEEPSEEK_API_KEY`, `IAM_URL` and `ts_api_url`. No username/password is
stored: the local UI sends each user's `Authorization: Bearer <token>` through
the client to the MCP server.

```bash
ssh ec2-user@"$IP" 'cd /opt/iam-mcp && cp .env.example .env && nano .env'
```

Then build and start everything:

```bash
ssh ec2-user@"$IP" \
  'APP_PORT=8080 APP_BIND=0.0.0.0 bash /opt/iam-mcp/deploy/remote-deploy.sh'
```

Check it:

```bash
ssh ec2-user@"$IP" 'docker ps; curl -s http://127.0.0.1:8080/health'
```

## What is deployed vs. what runs locally

**On EC2 (this Terraform + Compose):** only the MCP server and the FastAPI
client. **Locally:** the Next.js UI (`energy-mcp-ui/`) — it is not built or
deployed here.

The FastAPI client exposes:

| Endpoint | Purpose |
| --- | --- |
| `POST /chat` | Chat with the MCP agent (optional `Authorization: Bearer <jwt>`) |
| `GET /health` | Client + MCP tool status |
| `GET /tools` | Available MCP tools |
| `POST /clear_history` | Clear conversation state |

Run the UI on your laptop and point it at the deployed client:

```bash
cd energy-mcp-ui
NEXT_PUBLIC_MCP_BACKEND_SERVER_URL=http://<ec2-public-ip>:8080 npm run dev
# or through the SSH tunnel: http://localhost:8080
```

The MCP server itself listens on `8001` inside the compose network and on
`127.0.0.1:8001` on the host (for debugging). It is not exposed publicly; the
local UI talks to the client on `8080`, and the client talks to the server over
the private compose network.

## Recommended: SSH tunnel

Keep the app port loopback-only and forward it locally:

```bash
ssh -N -L 8080:127.0.0.1:8080 ec2-user@"$IP"
```

Then use `http://localhost:8080` as the UI backend / API base.

## Security notes

- Put TLS (ALB or nginx) in front; JWTs and the DeepSeek key travel in headers.
- Keep `DEEPSEEK_API_KEY` in `/opt/iam-mcp/.env` (git-ignored), never in the image.
- Each chat request can carry the caller's own Energybox JWT; the server never
  shares one user's token with another.

## Cost

Roughly $8/month for `t3.micro` + 8 GiB gp3 in `us-east-1`, plus egress.

## Destroy

```bash
terraform destroy
```
