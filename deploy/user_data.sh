#!/bin/bash
# Amazon Linux 2023 bootstrap: Docker Engine + compose/buildx CLI plugins.
#
# Runs from EC2 user_data on first boot. Safe to re-run manually:
#   sudo bash /opt/iam-mcp/deploy/user_data.sh
#
# Plugins come from Docker's CDN rather than the GitHub release redirects,
# which intermittently return HTTP 504 (seen on staging) and leave the host
# with Docker but no `docker compose`.
set -euxo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this script with sudo: sudo bash $0" >&2
  exit 1
fi

case "$(uname -m)" in
  x86_64) RPM_ARCH=x86_64 ;;
  aarch64) RPM_ARCH=aarch64 ;;
  *) echo "Unsupported architecture: $(uname -m)" >&2; exit 1 ;;
esac

# Pinned so the bootstrap is reproducible; bump deliberately.
DOCKER_PKG_BASE="https://download.docker.com/linux/centos/9/${RPM_ARCH}/stable/Packages"
COMPOSE_PKG="docker-compose-plugin-5.7.0-1.el9.${RPM_ARCH}.rpm"
BUILDX_PKG="docker-buildx-plugin-0.38.1-1.el9.${RPM_ARCH}.rpm"
PLUGIN_DIR="/usr/local/lib/docker/cli-plugins"

retry() {
  local attempt=1 max=5
  until "$@"; do
    if [ "$attempt" -ge "$max" ]; then
      echo "Command failed after $max attempts: $*" >&2
      return 1
    fi
    sleep $((attempt * 5))
    attempt=$((attempt + 1))
  done
}

# --- Swap (helps Docker builds on a 1 GiB t3.micro) -------------------------
if ! swapon --show | grep -q .; then
  dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# --- Docker -----------------------------------------------------------------
retry dnf install -y docker git rsync cpio
systemctl enable --now docker
usermod -aG docker ec2-user

# --- CLI plugins (compose + buildx) -----------------------------------------
# AL2023 ships buildx 0.12, but Compose v5 requires buildx >= 0.17. Install both
# into /usr/local/lib/docker/cli-plugins, which takes precedence over the RPM.
install_plugin() {
  local pkg="$1" binary="$2"
  local tmp
  tmp="$(mktemp -d)"
  (
    cd "$tmp"
    retry curl -fsSL --retry 5 --retry-all-errors --max-time 300 -O "${DOCKER_PKG_BASE}/${pkg}"
    rpm2cpio "$pkg" | cpio -idm --quiet
    install -m 0755 "usr/libexec/docker/cli-plugins/${binary}" "${PLUGIN_DIR}/${binary}"
  )
  rm -rf "$tmp"
}

mkdir -p "$PLUGIN_DIR"
install_plugin "$COMPOSE_PKG" docker-compose
install_plugin "$BUILDX_PKG" docker-buildx

docker compose version
docker buildx version

# --- App directory ----------------------------------------------------------
install -d -o ec2-user -g ec2-user /opt/iam-mcp

# Marker so a human / the deploy script can tell bootstrap finished.
touch /var/lib/iam-mcp-bootstrap-ok

docker version

echo
echo "Bootstrap complete."
echo "If 'docker ps' says permission denied, this shell predates the group change."
echo "Log out and back in, or run: newgrp docker"
