#!/bin/bash
# Amazon Linux 2023 bootstrap: Docker Engine + compose plugin + app directory.
set -euxo pipefail

# --- Swap (helps Docker builds on a 1 GiB t3.micro) -------------------------
if ! swapon --show | grep -q .; then
  dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# --- Docker -----------------------------------------------------------------
dnf install -y docker git rsync
systemctl enable --now docker
usermod -aG docker ec2-user

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64) COMPOSE_ARCH=x86_64 ;;
  aarch64) COMPOSE_ARCH=aarch64 ;;
  *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL \
  "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${COMPOSE_ARCH}" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# --- App directory ----------------------------------------------------------
install -d -o ec2-user -g ec2-user /opt/iam-mcp

docker version
docker compose version
