#!/usr/bin/env python3
"""
BeastPay MCP Server - Claude Code Integration

Exposes BeastPay payment gateway functions to Claude Code IDE.
Allows management of payments, merchants, and KYC directly from the editor.

Start: python mcp_beastpay/server.py
"""

import json
import os
import sys
from typing import Any, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class BeastPayMCPServer:
    """MCP Server for BeastPay payment gateway integration"""

    def __init__(self):
        self.resources = {}
        self.tools = {}
        self.init_resources()
        self.init_tools()

    def init_resources(self):
        """Register available resources"""
        self.resources = {
            # Payments
            'beastpay://payments/list': {
                'name': 'List Payments',
                'description': 'List all payments with filters (merchant, status, date)',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'merchant_id': {'type': 'string', 'description': 'Filter by merchant'},
                        'status': {'type': 'string', 'enum': ['pending', 'completed', 'failed']},
                        'limit': {'type': 'integer', 'default': 50},
                        'skip': {'type': 'integer', 'default': 0}
                    }
                }
            },
            'beastpay://payments/create': {
                'name': 'Create Payment',
                'description': 'Create a new payment/order',
                'inputSchema': {
                    'type': 'object',
                    'required': ['merchant_id', 'crypto', 'amount_usd'],
                    'properties': {
                        'merchant_id': {'type': 'string'},
                        'crypto': {'type': 'string', 'enum': ['BTC', 'ETH', 'USDC', 'USDT']},
                        'amount_usd': {'type': 'number', 'minimum': 0},
                        'webhook_url': {'type': 'string'},
                        'metadata': {'type': 'object'}
                    }
                }
            },
            # Merchants
            'beastpay://merchants/list': {
                'name': 'List Merchants',
                'description': 'List all registered merchants',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'kyc_status': {'type': 'string', 'enum': ['approved', 'pending', 'rejected']},
                        'country': {'type': 'string'},
                        'limit': {'type': 'integer', 'default': 50}
                    }
                }
            },
            'beastpay://merchants/register': {
                'name': 'Register Merchant',
                'description': 'Register a new merchant',
                'inputSchema': {
                    'type': 'object',
                    'required': ['company_name', 'email', 'country'],
                    'properties': {
                        'company_name': {'type': 'string'},
                        'email': {'type': 'string', 'format': 'email'},
                        'country': {'type': 'string'},
                        'webhook_url': {'type': 'string'}
                    }
                }
            },
            # Verification
            'beastpay://verification/run': {
                'name': 'Run KYC Verification',
                'description': 'Run full verification pipeline for merchant',
                'inputSchema': {
                    'type': 'object',
                    'required': ['merchant_id'],
                    'properties': {
                        'merchant_id': {'type': 'string'}
                    }
                }
            },
            # Providers
            'beastpay://providers/list': {
                'name': 'List Providers',
                'description': 'List all payment providers',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'verified_only': {'type': 'boolean', 'default': False},
                        'crypto': {'type': 'string'}
                    }
                }
            },
            'beastpay://providers/rank': {
                'name': 'Rank Providers',
                'description': 'Rank providers by quality/speed/fees',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'crypto': {'type': 'string', 'default': 'BTC'},
                        'sort_by': {'type': 'string', 'enum': ['quality', 'speed', 'fees']}
                    }
                }
            }
        }

    def init_tools(self):
        """Register available tools"""
        self.tools = {
            'list_payments': self.list_payments,
            'create_payment': self.create_payment,
            'list_merchants': self.list_merchants,
            'register_merchant': self.register_merchant,
            'run_verification': self.run_verification,
            'list_providers': self.list_providers,
            'rank_providers': self.rank_providers,
            'get_dashboard_stats': self.get_dashboard_stats,
        }

    # ============= Payment Operations =============

    async def list_payments(self, merchant_id: Optional[str] = None,
                           status: Optional[str] = None,
                           limit: int = 50, skip: int = 0) -> list:
        """List payments with optional filters"""
        try:
            from database import get_db
            db = await get_db()

            query = "SELECT * FROM payments WHERE 1=1"
            params = []

            if merchant_id:
                query += " AND merchant_id = ?"
                params.append(merchant_id)

            if status:
                query += " AND status = ?"
                params.append(status)

            query += f" ORDER BY created_at DESC LIMIT {limit} OFFSET {skip}"

            result = db.execute(query, params).fetchall()
            return [dict(row) for row in result]

        except Exception as e:
            return {'error': str(e)}

    async def create_payment(self, merchant_id: str, crypto: str,
                            amount_usd: float, webhook_url: Optional[str] = None,
                            metadata: Optional[dict] = None) -> dict:
        """Create a new payment"""
        try:
            from database import create_payment as db_create_payment
            from forceverify import best

            # Select best provider
            provider = best(crypto=crypto)

            # Create payment
            payment_id = await db_create_payment(
                merchant_id=merchant_id,
                provider=provider['provider_id'],
                amount_usd=amount_usd,
                crypto=crypto
            )

            return {
                'payment_id': payment_id,
                'provider': provider['provider_id'],
                'amount_usd': amount_usd,
                'crypto': crypto,
                'status': 'pending'
            }

        except Exception as e:
            return {'error': str(e)}

    # ============= Merchant Operations =============

    async def list_merchants(self, kyc_status: Optional[str] = None,
                            country: Optional[str] = None,
                            limit: int = 50) -> list:
        """List all merchants"""
        try:
            from database import get_db
            db = await get_db()

            query = "SELECT * FROM merchant_profiles WHERE 1=1"
            params = []

            if kyc_status:
                query += " AND kyc_status = ?"
                params.append(kyc_status)

            if country:
                query += " AND country = ?"
                params.append(country)

            query += f" LIMIT {limit}"

            result = db.execute(query, params).fetchall()
            return [dict(row) for row in result]

        except Exception as e:
            return {'error': str(e)}

    async def register_merchant(self, company_name: str, email: str,
                               country: str, webhook_url: Optional[str] = None) -> dict:
        """Register a new merchant"""
        try:
            from database import create_merchant

            merchant_id = await create_merchant(
                company_name=company_name,
                email=email,
                country=country,
                webhook_url=webhook_url
            )

            return {
                'merchant_id': merchant_id,
                'status': 'pending_verification',
                'next_steps': ['Upload company documents', 'Run KYC verification']
            }

        except Exception as e:
            return {'error': str(e)}

    # ============= Verification Operations =============

    async def run_verification(self, merchant_id: str) -> dict:
        """Run KYC verification pipeline"""
        try:
            from verification.engine import VerificationEngine
            from database import get_merchant

            merchant = await get_merchant(merchant_id)
            if not merchant:
                return {'error': f'Merchant {merchant_id} not found'}

            engine = VerificationEngine()
            result = await engine.run_pipeline(merchant_id)

            return result

        except Exception as e:
            return {'error': str(e)}

    # ============= Provider Operations =============

    async def list_providers(self, verified_only: bool = False,
                            crypto: Optional[str] = None) -> list:
        """List all payment providers"""
        try:
            from providers import provider_status_all

            providers = provider_status_all()

            if verified_only:
                providers = [p for p in providers if p.get('verified')]

            if crypto:
                providers = [p for p in providers
                           if crypto in p.get('support_crypto', [])]

            return providers

        except Exception as e:
            return {'error': str(e)}

    async def rank_providers(self, crypto: str = "BTC",
                            sort_by: str = "quality") -> list:
        """Rank providers by quality/speed/fees"""
        try:
            from forceverify import rank

            ranked = rank(crypto=crypto)

            if sort_by == 'speed':
                ranked.sort(key=lambda x: x.get('settlement_time_hours', 999))
            elif sort_by == 'fees':
                ranked.sort(key=lambda x: x.get('fees_pct', 999))
            # else: default quality sort

            return ranked

        except Exception as e:
            return {'error': str(e)}

    # ============= Dashboard =============

    async def get_dashboard_stats(self) -> dict:
        """Get dashboard statistics"""
        try:
            from database import get_db
            import sqlite3

            db = await get_db()

            stats = {
                'total_payments': db.execute(
                    "SELECT COUNT(*) FROM payments"
                ).fetchone()[0],
                'total_volume_usd': db.execute(
                    "SELECT COALESCE(SUM(amount_usd), 0) FROM payments WHERE status='completed'"
                ).fetchone()[0],
                'active_merchants': db.execute(
                    "SELECT COUNT(*) FROM merchant_profiles WHERE active=1"
                ).fetchone()[0],
                'kyc_approvals': db.execute(
                    "SELECT COUNT(*) FROM kyc_records WHERE decision='APPROVED'"
                ).fetchone()[0],
                'pending_kyc': db.execute(
                    "SELECT COUNT(*) FROM kyc_records WHERE decision='PENDING_REVIEW'"
                ).fetchone()[0],
            }

            return stats

        except Exception as e:
            return {'error': str(e)}

    # ============= Server Methods =============

    def list_resources(self):
        """List all available resources"""
        return list(self.resources.keys())

    def get_resource(self, uri: str) -> dict:
        """Get resource definition"""
        return self.resources.get(uri, {'error': 'Resource not found'})

    async def call_tool(self, tool_name: str, args: dict) -> Any:
        """Call a tool"""
        if tool_name not in self.tools:
            return {'error': f'Tool {tool_name} not found'}

        tool = self.tools[tool_name]
        return await tool(**args)


async def main():
    """Start MCP server"""
    import asyncio
    from aiohttp import web

    server = BeastPayMCPServer()

    async def handle_list_resources(request):
        """GET /resources - list resources"""
        return web.json_response({'resources': server.list_resources()})

    async def handle_get_resource(request):
        """GET /resources/{uri} - get resource"""
        uri = request.match_info.get('uri', '')
        resource = server.get_resource(uri)
        return web.json_response(resource)

    async def handle_call_tool(request):
        """POST /tools/{name} - call tool"""
        name = request.match_info.get('name', '')
        data = await request.json()
        result = await server.call_tool(name, data)
        return web.json_response({'result': result})

    app = web.Application()
    app.router.add_get('/resources', handle_list_resources)
    app.router.add_get('/resources/{uri}', handle_get_resource)
    app.router.add_post('/tools/{name}', handle_call_tool)

    # Health check
    app.router.add_get('/health', lambda r: web.json_response({'status': 'ok'}))

    port = int(os.getenv('MCP_PORT', 3000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', port)
    await site.start()

    print(f"🚀 BeastPay MCP Server running on http://127.0.0.1:{port}")
    print(f"📊 Resources: {len(server.resources)}")
    print(f"🔧 Tools: {len(server.tools)}")
    print(f"🔗 Configure in .claude/settings.json")
    print()
    print("Available resources:")
    for uri in sorted(server.list_resources()):
        print(f"  • {uri}")
    print()
    print("Press Ctrl+C to stop")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n✅ Shutting down...")
        await runner.cleanup()


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
