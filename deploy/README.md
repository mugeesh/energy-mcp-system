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
| Software | Docker Engine + compose/buildx CLI plugins (from Docker's CDN), git, rsync, 2 GiB swap |
| App port | host `8080` → client container `8000` (MCP server is only on the compose network plus host loopback `8001`) |

`mcp_security_group_id` attaches the existing SG that allows port `8080`.
`mcp_ingress_cidrs` is empty by default; leave it empty and use the SSH tunnel,
or set it to have Terraform create a public ingress SG for the app port.

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

Outputs include `instance_id`, `public_ip`, `private_ip`, `ami_id`,
`instance_type`, `ssh_command`, `ssh_tunnel_command`, `app_local_url`,
`app_public_url` (and the legacy `mcp_local_url` / `mcp_public_url` aliases).

## Deploy the stack

Copy the project (including `docker-compose.yml`, `mcp-server-client/` and
`deploy/`) to `/opt/iam-mcp`:

```bash
IP=$(terraform output -raw public_ip)
tar czf - \
  --exclude .venv --exclude __pycache__ --exclude node_modules \
  --exclude './energy-mcp-ui/.next' --exclude .DS_Store \
  --exclude .env --exclude .git \
  --exclude './deploy/.terraform*' \
  --exclude './deploy/terraform.tfstate*' \
  -C .. . \
  | ssh ec2-user@"$IP" \
      'sudo mkdir -p /opt/iam-mcp && sudo chown ec2-user:ec2-user /opt/iam-mcp && tar xzf - -C /opt/iam-mcp'
```

The `./` prefix in the `deploy/` excludes matters: `tar -C .. .` stores paths as
`./deploy/...`, so a bare `deploy/.terraform*` pattern does not match on macOS
`bsdtar`.

On the instance, create `/opt/iam-mcp/.env` from `.env.example`. Only
`DEEPSEEK_API_KEY` is required — `IAM_URL`, `IAM_API_PREFIX` and `ts_api_url`
already default to the staging endpoints in `.env.example` and
`docker-compose.yml`. No username/password is stored: the local UI sends each
user's `Authorization: Bearer <token>` through the client to the MCP server.

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

Verify the host bootstrap finished before deploying (the marker is written at
the end of `user_data.sh`):

```bash
ssh ec2-user@"$IP" \
  'ls /var/lib/iam-mcp-bootstrap-ok && docker compose version && docker buildx version'
```

If you SSH in while cloud-init is still running, that shell predates the
`docker` install and `usermod -aG docker`, so `docker` may be missing or
"permission denied" **in that session only**. Reconnect and re-check; do not
re-run the bootstrap for this.

## What is deployed vs. what runs locally

**On EC2 (this Terraform + Compose):** only the MCP server and the FastAPI
client. **Locally:** the Next.js UI (`energy-mcp-ui/`) — it is not built or
deployed here.

The FastAPI client exposes:

| Endpoint | Purpose |
| --- | --- |
| `POST /chat` | Chat with the MCP agent — requires `Authorization: Bearer <jwt>` (401 otherwise) |
| `GET /health` | Client + MCP tool status |
| `GET /tools` | Available MCP tools |
| `POST /clear_history` | No-op for API compatibility; chat is stateless |

The client keeps no server-side conversation history: every `/chat` request
carries the history it wants the agent to see.

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

If you started the stack with `APP_BIND=0.0.0.0`, re-run the deploy script with
the loopback bind so port 8080 is no longer reachable from the internet:

```bash
ssh ec2-user@"$IP" \
  'APP_PORT=8080 APP_BIND=127.0.0.1 bash /opt/iam-mcp/deploy/remote-deploy.sh'
```

## Troubleshooting

### `docker: command not found` (or `permission denied`) on the instance

First check whether cloud-init has actually finished — it installs Docker:

```bash
sudo cloud-init status --long
id -nG
```

- `status: running` → wait (`sudo cloud-init status --wait`) or reconnect; your
  shell may predate the install and the `docker` group addition.
- `status: done` but `docker` is missing → the bootstrap failed; continue below.
- `docker` exists but `docker ps` says permission denied → you are not in the
  `docker` group in this session; log out and back in.

`user_data.sh` is a **cloud-init script: it runs once, on the instance's first
boot**. `terraform apply` does not re-run it on a live instance (`main.tf` also
sets `ignore_changes = [user_data]`), so if cloud-init failed there is no
Docker on the host.

See what happened:

```bash
sudo tail -n 80 /var/log/cloud-init-output.log
```

Install it now — the script is safe to re-run (swap creation is guarded and the
`dnf`/compose steps are idempotent):

```bash
sudo bash /opt/iam-mcp/deploy/user_data.sh
```

If the project has not been copied yet, run the equivalent directly:

```bash
sudo dnf install -y docker git rsync
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
```

Then **log out and back in** so the `docker` group membership applies, and
verify:

```bash
exit
ssh ec2-user@<instance-ip>
docker ps
docker compose version
```

`remote-deploy.sh` now preflights Docker, the compose plugin, buildx and daemon
access, and exits with these instructions instead of a raw compose error.

### `compose build requires buildx 0.17.0 or later`

AL2023's `docker` package ships **buildx 0.12**, but Compose v5 needs
**buildx >= 0.17**. `user_data.sh` installs both plugins (compose and buildx)
from Docker's CDN into `/usr/local/lib/docker/cli-plugins`. If the host was
bootstrapped before that, re-run it:

```bash
sudo bash /opt/iam-mcp/deploy/user_data.sh
docker compose version
docker buildx version   # must be >= 0.17
```

The plugins are pinned (`docker-compose-plugin-5.7.0`,
`docker-buildx-plugin-0.38.1`) and fetched from
`download.docker.com/linux/centos/9/<arch>/stable/Packages`, because GitHub's
release redirects intermittently return HTTP 504 during cloud-init.

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
