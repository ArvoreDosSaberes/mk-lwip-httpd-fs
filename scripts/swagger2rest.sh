#!/usr/bin/env bash
# swagger2rest.sh - Wrapper para executar o script Python swagger2rest.py
#
# Projeto : STM32-F429zi-http
# Proposito: Gerar descricoes de endpoints REST (headers .h/.c) a partir de
#            um arquivo Swagger/OpenAPI em JSON.
#
# Uso basico:
#   ./scripts/swagger2rest.sh <swagger_dir> -o <dest_header> -v <version>
#
# Os parametros sao repassados diretamente ao swagger2rest.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# SUBPROJ_DIR deve apontar para a raiz "makefs" (ja calculada em PROJECT_ROOT)
SUBPROJ_DIR="${PROJECT_ROOT}"

PYTHON=""

if [[ -x "${SUBPROJ_DIR}/venv/bin/python" ]]; then
  PYTHON="${SUBPROJ_DIR}/venv/bin/python"
elif [[ -x "${PROJECT_ROOT}/venv-mk-lwip-httpd-fs/bin/python" ]]; then
  PYTHON="${PROJECT_ROOT}/venv-mk-lwip-httpd-fs/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON="python"
else
  echo "Erro: Python nao encontrado no sistema nem em ambientes virtuais conhecidos." >&2
  exit 1
fi

# repassa todos os argumentos para o script swagger2rest.py
exec "${PYTHON}" "${SUBPROJ_DIR}/swagger/swagger2rest.py" "$@"
