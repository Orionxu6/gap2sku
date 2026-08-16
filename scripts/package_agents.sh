#!/usr/bin/env bash
# Package agent directories into zips for AgentTeams Worker CR .spec.package.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_DIR="${DIR}/agents"
PKG_DIR="${DIR}/packages"
mkdir -p "${PKG_DIR}"

if [ ! -d "${AGENTS_DIR}" ]; then
  echo "[package] no agents/ dir"; exit 0
fi

for agent_dir in "${AGENTS_DIR}"/*/; do
  name=$(basename "${agent_dir}")
  zip="${PKG_DIR}/${name}.zip"
  (cd "${AGENTS_DIR}" && zip -qr "${zip}" "${name}")
  echo "[package] ${name} -> ${zip}"
done
echo "[package] done"
