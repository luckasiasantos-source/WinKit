#!/usr/bin/env bash
# Verificação completa antes de commitar (CLAUDE.md). Para no primeiro erro.
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_SYSTEM_CERTS="${UV_SYSTEM_CERTS:-1}"
unset UV_NATIVE_TLS || true

echo "== ruff (lint)";    uv run ruff check src tests
echo "== ruff (formato)"; uv run ruff format --check src tests
echo "== mypy";           uv run mypy
echo "== import-linter";  uv run lint-imports
echo "== pytest";         uv run pytest -q "$@"
echo "== OK"
