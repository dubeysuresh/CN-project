#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${1:-${PROJECT_DIR}/../.venv}"

if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    python3.11 -m venv "${VENV_DIR}"
fi

"${VENV_DIR}/bin/python" -m pip install 'setuptools==58.0.4' wheel
"${VENV_DIR}/bin/python" -m pip install --no-build-isolation -r "${PROJECT_DIR}/requirements.txt"

# Ryu 4.34 predates Eventlet's removal of ALREADY_HANDLED. Apply the same
# compatibility behavior used in Ryu upstream after the PyPI release.
"${VENV_DIR}/bin/python" - <<'PY'
from pathlib import Path
import ryu

path = Path(ryu.__file__).parent / "app" / "wsgi.py"
source = path.read_text()
old = "    from eventlet.wsgi import ALREADY_HANDLED\n    _ALREADY_HANDLED = ALREADY_HANDLED"
new = "    import eventlet.wsgi\n    _ALREADY_HANDLED = getattr(eventlet.wsgi, 'ALREADY_HANDLED', None)"
if old in source:
    path.write_text(source.replace(old, new, 1))
elif new not in source:
    raise SystemExit(f"Unexpected Ryu WSGI implementation: {path}")
print(f"Ryu/Eventlet compatibility checked: {path}")
PY

"${VENV_DIR}/bin/python" -m pip check
"${VENV_DIR}/bin/ryu-manager" --help >/dev/null
echo "Ready: ${VENV_DIR}"
