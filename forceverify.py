"""
ForceVerify: Provider Ranking & Verification Dashboard

Scores and ranks all payment providers on:
- Verification status (live keys, production config)
- Settlement speed
- Fee structure
- KYC coverage
- Currency support
- Crypto support
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from providers import (
    _is_production,
    PROVIDER_METADATA,
)
from provider_selector import ProviderSelector
from config import settings

logger = logging.getLogger(__name__)


@dataclass
class ProviderRanking:
    """Provider ranking with scores."""
    provider_id: str
    name: str
    type: str
    verified: bool  # Has live keys
    verification_score: float  # 0-100
    speed_score: float  # 0-100 (faster = higher)
    fee_score: float  # 0-100 (cheaper = higher)
    coverage_score: float  # 0-100 (more currencies = higher)
    kyc_score: float  # 0-100 (KYC tier support)
    overall_score: float  # Weighted average
    settlement_minutes: int
    fee_pct: float
    supported_currencies: List[str]
    no_kyc_limit_usd: float
    recommendation: str


class ForceVerify:
    """Provider verification and ranking engine."""

    # Weights for overall score (must sum to 100)
    WEIGHT_VERIFICATION = 30  # Is it live?
    WEIGHT_SPEED = 20  # Settlement speed
    WEIGHT_FEE = 20  # Fee structure
    WEIGHT_COVERAGE = 20  # Currency support
    WEIGHT_KYC = 10  # KYC flexibility

    @classmethod
    def rank_all(cls) -> List[ProviderRanking]:
        """Rank all providers overall score."""
        rankings = []

        for provider_id, meta in PROVIDER_METADATA.items():
            ranking = cls.rank_provider(provider_id, meta)
            rankings.append(ranking)

        # Sort by overall score (descending)
        rankings.sort(key=lambda x: -x.overall_score)

        return rankings

    @classmethod
    def rank_for_amount(
        cls,
        amount_usd: float,
        fiat_currency: str = "USD",
    ) -> List[ProviderRanking]:
        """Rank providers for specific amount and currency."""
        rankings = []

        for provider_id, meta in PROVIDER_METADATA.items():
            # Skip if doesn't support fiat currency
            if fiat_currency not in meta.get("supported_fiats", []):
                continue

            # Skip if amount exceeds limit
            if amount_usd > meta.get("max_limit_usd", 0):
                continue

            ranking = cls.rank_provider(provider_id, meta)
            rankings.append(ranking)

        # Sort by overall score (descending)
        rankings.sort(key=lambda x: -x.overall_score)

        return rankings

    @classmethod
    def best(
        cls,
        crypto: str = "USDC",
        amount_usd: Optional[float] = None,
    ) -> Optional[ProviderRanking]:
        """Get single best provider."""
        if amount_usd:
            rankings = cls.rank_for_amount(amount_usd)
        else:
            rankings = cls.rank_all()

        if rankings:
            return rankings[0]
        return None

    @classmethod
    def rank_provider(
        cls,
        provider_id: str,
        meta: Dict,
    ) -> ProviderRanking:
        """Score single provider."""
        verified = _is_production(provider_id)

        # Verification score (30 points max)
        verification_score = 100.0 if verified else 30.0

        # Speed score (20 points max) - faster = higher
        settlement_minutes = ProviderSelector.SETTLEMENT_TIMES.get(provider_id, 60)
        # Normalize: 3 min = 100, 60 min = 50, 1440 min (1 day) = 10
        speed_score = max(10, min(100, 100 - (settlement_minutes - 3) * 0.7))

        # Fee score (20 points max) - cheaper = higher
        fee_pct = meta.get("fee_pct", 0)
        # Normalize: 0% = 100, 1% = 90, 3% = 70, 5% = 50
        fee_score = max(10, min(100, 100 - (fee_pct * 20)))

        # Coverage score (20 points max) - more currencies = higher
        num_currencies = len(meta.get("supported_fiats", []))
        coverage_score = min(100, 30 + (num_currencies * 5))  # Base 30 + 5 per currency

        # KYC score (10 points max) - easier KYC = higher
        kyc_type = meta.get("kyc_type", "requires_kyc")
        kyc_map = {
            "none": 100,
            "email_only": 80,
            "email_and_name": 70,
            "requires_kyc": 40,
        }
        kyc_score = kyc_map.get(kyc_type, 40)

        # Calculate weighted overall score
        overall_score = (
            (verification_score * cls.WEIGHT_VERIFICATION / 100) +
            (speed_score * cls.WEIGHT_SPEED / 100) +
            (fee_score * cls.WEIGHT_FEE / 100) +
            (coverage_score * cls.WEIGHT_COVERAGE / 100) +
            (kyc_score * cls.WEIGHT_KYC / 100)
        )

        # Generate recommendation
        recommendation = cls._get_recommendation(
            provider_id=provider_id,
            verified=verified,
            fee=fee_pct,
            settlement=settlement_minutes,
            kyc_type=kyc_type,
        )

        return ProviderRanking(
            provider_id=provider_id,
            name=meta.get("name", provider_id),
            type=meta.get("type", "unknown"),
            verified=verified,
            verification_score=verification_score,
            speed_score=speed_score,
            fee_score=fee_score,
            coverage_score=coverage_score,
            kyc_score=kyc_score,
            overall_score=overall_score,
            settlement_minutes=settlement_minutes,
            fee_pct=fee_pct,
            supported_currencies=meta.get("supported_fiats", []),
            no_kyc_limit_usd=meta.get("no_kyc_limit_usd", 0),
            recommendation=recommendation,
        )

    @staticmethod
    def _get_recommendation(
        provider_id: str,
        verified: bool,
        fee: float,
        settlement: int,
        kyc_type: str,
    ) -> str:
        """Generate human-readable recommendation."""
        if not verified:
            return f"⚠️  SANDBOX - needs {provider_id.upper()} live keys"

        if fee == 0:
            return "⭐⭐⭐ BEST FEE - 0% (recommend for all amounts)"

        if settlement <= 5:
            return "⚡ FASTEST - use for urgent payments"

        if kyc_type == "none":
            return "🔓 NO KYC - use for small amounts"

        if settlement <= 10:
            return "⚡ FAST - good all-around choice"

        return "✅ AVAILABLE - standard settlement"

    @classmethod
    def health_check(cls) -> Dict:
        """Get health status of all providers."""
        rankings = cls.rank_all()

        live = [r for r in rankings if r.verified]
        sandbox = [r for r in rankings if not r.verified]

        return {
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "live_count": len(live),
            "sandbox_count": len(sandbox),
            "total_count": len(rankings),
            "live_providers": [r.provider_id for r in live],
            "sandbox_providers": [r.provider_id for r in sandbox],
            "top_3_overall": [asdict(r) for r in rankings[:3]],
            "best_fee": rankings[0],  # Already sorted by overall_score
        }

    @classmethod
    def export_dashboard_data(cls) -> Dict:
        """Export data for dashboard visualization."""
        rankings = cls.rank_all()

        return {
            "providers": [asdict(r) for r in rankings],
            "summary": {
                "live": sum(1 for r in rankings if r.verified),
                "sandbox": sum(1 for r in rankings if not r.verified),
                "total": len(rankings),
                "avg_fee": sum(r.fee_pct for r in rankings) / len(rankings),
                "avg_settlement_min": sum(r.settlement_minutes for r in rankings) / len(rankings),
            },
            "by_type": cls._group_by_type(rankings),
            "by_status": {
                "live": [asdict(r) for r in rankings if r.verified],
                "sandbox": [asdict(r) for r in rankings if not r.verified],
            },
        }

    @staticmethod
    def _group_by_type(rankings: List[ProviderRanking]) -> Dict:
        """Group rankings by provider type."""
        grouped = {}
        for ranking in rankings:
            ptype = ranking.type
            if ptype not in grouped:
                grouped[ptype] = []
            grouped[ptype].append(asdict(ranking))
        return grouped


# CLI usage
def print_dashboard():
    """Print provider dashboard to console."""
    rankings = ForceVerify.rank_all()

    print("\n" + "=" * 120)
    print("  FORCEVERIFY PROVIDER RANKING DASHBOARD".center(120))
    print("=" * 120)

    # Header
    print(
        f"{'Provider':<15} {'Type':<15} {'Status':<10} {'Overall':<10} "
        f"{'Verification':<15} {'Speed':<8} {'Fee':<8} {'Coverage':<10} {'Recommendation':<30}"
    )
    print("-" * 120)

    # Rankings
    for i, r in enumerate(rankings, 1):
        status = "🟢 LIVE" if r.verified else "🟡 SANDBOX"
        print(
            f"{r.provider_id:<15} {r.type:<15} {status:<10} "
            f"{r.overall_score:>8.1f} {r.verification_score:>12.1f}/100 "
            f"{r.speed_score:>7.1f}/100 {r.fee_pct:>7.1f}% "
            f"{len(r.supported_currencies):>9} {r.recommendation:<30}"
        )

    print("=" * 120)
    print(f"\n✅ LIVE: {sum(1 for r in rankings if r.verified)} providers")
    print(f"⚠️  SANDBOX: {sum(1 for r in rankings if not r.verified)} providers")


if __name__ == "__main__":
    print_dashboard()
