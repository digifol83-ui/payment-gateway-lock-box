from .transak import TransakProvider
from .moonpay import MoonPayProvider
from .nowpayments import NowPaymentsProvider
from .stripe import StripeProvider

PROVIDERS = {
    "transak":     TransakProvider(),
    "moonpay":     MoonPayProvider(),
    "nowpayments": NowPaymentsProvider(),
    "stripe":      StripeProvider(),
}

def get_provider(name: str):
    return PROVIDERS.get(name.lower())
