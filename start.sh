#!/usr/bin/env bash
# BeastPay — start server
set -e
cd "$(dirname "$0")"
source .env
exec uvicorn server:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
