#!/usr/bin/env bash
# makefsdata_py.sh - Wrapper para executar o script Python makefsdata.py
#
# Projeto : mk-lwip-httpd-fs
# Proposito: Converter arvore de arquivos web em fsdata.c (httpd lwIP) via Python
# Autor   : Carlos Delfino
# Data    : 2025-12-09
# Dependencias: Python 3; ambiente virtual opcional em
#            - MakeFSdataProjPlusExample/venv
#            - venv-mk-lwip-httpd-fs/ na raiz do projeto
#
# Uso:
#   ./scripts/makefsdata_py.sh [targetdir] [opções]
# Os parâmemetros são repassados diretamente ao makefsdata.py.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# SUBPROJ_DIR deve apontar para a raiz "makefs" (já calculada em PROJECT_ROOT)
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

exec "${PYTHON}" "${SUBPROJ_DIR}/makefsdata/makefsdata.py" "$@"
