"""BeastPay MCP Server - Claude Code Integration

Enables Claude Code IDE to interact with BeastPay payment gateway.

Usage:
    python mcp_beastpay/server.py

Configuration in .claude/settings.json:
    {
      "mcpServers": {
        "beastpay": {
          "command": "python",
          "args": ["/path/to/payment-gateway/mcp_beastpay/server.py"]
        }
      }
    }

Then use in Claude Code:
    @beastpay Create payment: merchant_abc, 100 USD, BTC
    @beastpay List all payments
    @beastpay Show KYC status for merchant_xyz
"""

__version__ = "1.0.0"
__author__ = "BeastPay Development"

from .server import BeastPayMCPServer

__all__ = ['BeastPayMCPServer']
