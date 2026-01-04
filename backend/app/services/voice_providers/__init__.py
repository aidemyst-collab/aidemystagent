"""
Voice Provider Module

Supports:
- Twilio (Global)
- Etisalat CPaaS (UAE/MENA)
"""

from .base import VoiceProvider, VoiceProviderError
from .twilio_provider import TwilioProvider
from .etisalat_provider import EtisalatProvider
from .security import (
    verify_webhook_security,
    validate_ip_whitelist,
    validate_basic_auth,
    generate_basic_auth_credentials,
    build_webhook_url_with_auth,
    get_client_ip,
    TWILIO_IP_RANGES,
    ETISALAT_IP_RANGES,
)

PROVIDERS = {
    "twilio": TwilioProvider,
    "etisalat": EtisalatProvider,
}


def get_voice_provider(provider_name: str, credentials: dict) -> VoiceProvider:
    """
    Factory function to get a voice provider instance.

    Args:
        provider_name: Either 'twilio' or 'etisalat'
        credentials: Provider-specific credentials dict

    Returns:
        VoiceProvider instance

    Raises:
        ValueError: If provider_name is not supported
    """
    if provider_name not in PROVIDERS:
        raise ValueError(
            f"Unknown voice provider: {provider_name}. "
            f"Supported providers: {', '.join(PROVIDERS.keys())}"
        )
    return PROVIDERS[provider_name](credentials)


__all__ = [
    "VoiceProvider",
    "VoiceProviderError",
    "TwilioProvider",
    "EtisalatProvider",
    "get_voice_provider",
    "PROVIDERS",
    # Security
    "verify_webhook_security",
    "validate_ip_whitelist",
    "validate_basic_auth",
    "generate_basic_auth_credentials",
    "build_webhook_url_with_auth",
    "get_client_ip",
    "TWILIO_IP_RANGES",
    "ETISALAT_IP_RANGES",
]
