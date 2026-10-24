#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-${PROJECT_DIR}/../.venv}"
exec "${VENV_DIR}/bin/ryu-manager" \
    --ofp-listen-host 127.0.0.1 --ofp-tcp-listen-port 6653 \
    --wsapi-host 127.0.0.1 --wsapi-port 8080 \
    "${PROJECT_DIR}/firewall_controller.py"
