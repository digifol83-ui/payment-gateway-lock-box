"""
Provider Selector: Smart failover logic for fiat-to-crypto payment routing.

Selects the best provider(s) based on:
1. Amount (KYC tier requirements)
2. Fiat currency support
3. Crypto currency support
4. Settlement speed
5. Fee optimization
6. Live status (production keys)
"""

from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from providers import (
    get_provider,
    get_provider_metadata,
    list_production_fiat_to_crypto,
    _is_production,
    PROVIDER_METADATA,
)
from config import settings

logger = logging.getLogger(__name__)


class SelectionStrategy(Enum):
    """Provider selection strategies."""
    BEST_VERIFIED = "best_verified"  # Highest verified + lowest fee
    FASTEST = "fastest"  # Fastest settlement time
    CHEAPEST = "cheapest"  # Lowest fee
    COVERAGE = "coverage"  # Best currency coverage
    BALANCED = "balanced"  # Balance of speed, fee, coverage


@dataclass
class ProviderScore:
    """Score for provider ranking."""
    provider_id: str
    score: float
    verified: bool
    fee_pct: float
    settlement_minutes: int
    kyc_tier: str
    reason: str


class ProviderSelector:
    """Intelligent provider selection for payment routing."""

    # Settlement time in minutes (for sorting)
    SETTLEMENT_TIMES = {
        "bleap": 3,
        "kast": 5,
        "swapin": 8,
        "guardarian": 20,
        "charge": 10,
        "transak": 30,
        "finchpay": 15,
        "moonpay": 30,
        "nowpayments": 10,
        "metamask": 7,
        "stripe": 2880,  # T+2 days
        "ziina": 1440,  # T+1 day
        "coinremitter": 10,
        "plisio": 10,
    }

    @classmethod
    def select_provider(
        cls,
        amount_usd: float,
        fiat_currency: str,
        crypto_currency: str = "USDC",
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
        exclude_providers: List[str] = None,
    ) -> Optional[str]:
        """
        Select single best provider for the given criteria.

        Args:
            amount_usd: Transaction amount in USD
            fiat_currency: Source currency (USD, EUR, GBP, AED, etc.)
            crypto_currency: Target crypto (USDC, BTC, ETH, etc.)
            strategy: Selection strategy
            exclude_providers: Providers to skip (for fallback)

        Returns:
            Provider ID or None if no suitable provider found
        """
        candidates = cls.rank_providers(
            amount_usd=amount_usd,
            fiat_currency=fiat_currency,
            crypto_currency=crypto_currency,
            strategy=strategy,
            exclude_providers=exclude_providers,
        )

        if candidates:
            best = candidates[0]
            logger.info(
                f"Selected provider: {best.provider_id} "
                f"(score: {best.score:.2f}, fee: {best.fee_pct}%, "
                f"kyc_tier: {best.kyc_tier})"
            )
            return best.provider_id

        logger.warning(
            f"No suitable provider for {amount_usd} {fiat_currency} → {crypto_currency}"
        )
        return None

    @classmethod
    def rank_providers(
        cls,
        amount_usd: float,
        fiat_currency: str,
        crypto_currency: str = "USDC",
        strategy: SelectionStrategy = SelectionStrategy.BALANCED,
        exclude_providers: List[str] = None,
        top_n: int = 5,
    ) -> List[ProviderScore]:
        """
        Rank all suitable providers by score.

        Returns list of top N providers ranked by strategy.
        """
        if amount_usd <= 0:
            logger.warning("Invalid provider selection amount: %s", amount_usd)
            return []

        exclude_providers = exclude_providers or []
        candidates = []

        for provider_id, meta in PROVIDER_METADATA.items():
            if provider_id in exclude_providers:
                continue

            # Basic compatibility checks
            if meta.get("type") not in ["fiat-to-crypto", "fiat-only"]:
                continue

            if fiat_currency not in meta.get("supported_fiats", []):
                continue

            if amount_usd > meta.get("max_limit_usd", 0):
                continue

            # Determine KYC tier
            kyc_tier = cls._get_kyc_tier(amount_usd)

            # Verify provider is live
            verified = _is_production(provider_id)

            # Calculate score based on strategy
            score = cls._calculate_score(
                provider_id=provider_id,
                meta=meta,
                strategy=strategy,
                verified=verified,
                amount_usd=amount_usd,
            )

            fee_pct = meta.get("fee_pct", 0)
            settlement_minutes = cls.SETTLEMENT_TIMES.get(provider_id, 60)

            candidates.append(
                ProviderScore(
                    provider_id=provider_id,
                    score=score,
                    verified=verified,
                    fee_pct=fee_pct,
                    settlement_minutes=settlement_minutes,
                    kyc_tier=kyc_tier,
                    reason=f"Fee: {fee_pct}%, Settlement: {settlement_minutes}min, "
                    f"Verified: {verified}",
                )
            )

        # Sort by score descending
        candidates.sort(key=lambda x: -x.score)

        logger.debug(
            f"Ranked {len(candidates)} providers for "
            f"{amount_usd} {fiat_currency} (strategy: {strategy.value})"
        )

        return candidates[:top_n]

    @classmethod
    def _get_kyc_tier(cls, amount_usd: float) -> str:
        """Determine KYC tier based on amount."""
        kyc_free = settings.KYC_FREE_LIMIT_USD
        kyc_sumsub = settings.KYC_SUMSUB_LIMIT

        if amount_usd < kyc_free:
            return "none"
        elif amount_usd < kyc_sumsub:
            return "email_kyc"
        else:
            return "full_kyc"

    @classmethod
    def _calculate_score(
        cls,
        provider_id: str,
        meta: Dict,
        strategy: SelectionStrategy,
        verified: bool,
        amount_usd: float,
    ) -> float:
        """Calculate provider score based on strategy."""
        base_score = 0.0

        # Verification bonus
        if verified:
            base_score += 50.0
        else:
            base_score += 10.0  # Sandbox penalty

        fee = meta.get("fee_pct", 0)
        settlement = cls.SETTLEMENT_TIMES.get(provider_id, 60)

        if strategy == SelectionStrategy.BEST_VERIFIED:
            # Heavily favor verified + lowest fee
            base_score += (100 - fee) * 2  # Fee optimization
            base_score += (1000 - settlement) / 10  # Settlement bonus
            return base_score

        elif strategy == SelectionStrategy.FASTEST:
            # Minimize settlement time
            base_score += (1000 - settlement) * 2
            base_score += (100 - fee)  # Secondary: fee
            return base_score

        elif strategy == SelectionStrategy.CHEAPEST:
            # Lowest fee
            base_score += (100 - fee) * 3
            base_score += (1000 - settlement) / 20
            return base_score

        elif strategy == SelectionStrategy.COVERAGE:
            # Best currency support
            num_fiats = len(meta.get("supported_fiats", []))
            base_score += num_fiats * 5
            base_score += (100 - fee)
            return base_score

        else:  # BALANCED (default)
            # Balance all factors
            base_score += (100 - fee) * 1.5  # Fee (weighted)
            base_score += (1000 - settlement) / 5  # Settlement
            base_score += len(meta.get("supported_fiats", [])) * 2  # Coverage
            return base_score

    @classmethod
    def get_failover_chain(
        cls,
        amount_usd: float,
        fiat_currency: str,
        crypto_currency: str = "USDC",
    ) -> List[str]:
        """
        Get ordered list of providers for failover.

        Returns list of provider IDs in order of preference.
        """
        chain = []
        excluded = set()

        for _ in range(5):  # Max 5 providers in chain
            provider = cls.select_provider(
                amount_usd=amount_usd,
                fiat_currency=fiat_currency,
                crypto_currency=crypto_currency,
                strategy=SelectionStrategy.BALANCED,
                exclude_providers=list(excluded),
            )

            if not provider:
                break

            chain.append(provider)
            excluded.add(provider)

        logger.info(f"Failover chain: {chain}")
        return chain

    @classmethod
    def health_check(cls) -> Dict[str, any]:
        """Check health of all providers."""
        health = {
            "live_providers": 0,
            "sandbox_providers": 0,
            "total_providers": len(PROVIDER_METADATA),
            "providers": {},
        }

        for provider_id in PROVIDER_METADATA.keys():
            is_live = _is_production(provider_id)
            status = "LIVE" if is_live else "SANDBOX"

            if is_live:
                health["live_providers"] += 1
            else:
                health["sandbox_providers"] += 1

            health["providers"][provider_id] = {
                "status": status,
                "verified": is_live,
                "type": PROVIDER_METADATA[provider_id].get("type"),
            }

        return health


# Convenience functions
def select_best_provider(
    amount_usd: float,
    fiat_currency: str,
    crypto_currency: str = "USDC",
) -> Optional[str]:
    """Wrapper: Select best provider (balanced strategy)."""
    return ProviderSelector.select_provider(
        amount_usd=amount_usd,
        fiat_currency=fiat_currency,
        crypto_currency=crypto_currency,
        strategy=SelectionStrategy.BALANCED,
    )


def get_provider_options(
    amount_usd: float,
    fiat_currency: str,
    limit: int = 3,
) -> List[ProviderScore]:
    """Wrapper: Get top N provider options."""
    return ProviderSelector.rank_providers(
        amount_usd=amount_usd,
        fiat_currency=fiat_currency,
        strategy=SelectionStrategy.BALANCED,
        top_n=limit,
    )


def get_failover_chain(
    amount_usd: float,
    fiat_currency: str,
) -> List[str]:
    """Wrapper: Get failover provider chain."""
    return ProviderSelector.get_failover_chain(
        amount_usd=amount_usd,
        fiat_currency=fiat_currency,
    )
