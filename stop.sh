#!/usr/bin/env bash
# BeastPay — stop server
pkill -f "uvicorn server:app" && echo "Server stopped." || echo "Server not running."
