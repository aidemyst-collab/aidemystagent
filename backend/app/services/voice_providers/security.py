"""
Voice Webhook Security Module

Provides IP whitelisting and Basic Auth validation for voice provider webhooks.
"""

import ipaddress
import base64
import secrets
import logging
from typing import Optional, List, Tuple
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# Twilio IP ranges (as of 2024 - check https://www.twilio.com/docs/sip-trunking/ip-addresses)
# These should be updated periodically or fetched dynamically
TWILIO_IP_RANGES = [
    # North America - Virginia
    "54.172.60.0/23",
    "54.172.60.0/24",
    "54.172.61.0/24",
    # North America - Oregon
    "54.244.51.0/24",
    # Europe - Ireland
    "54.171.127.192/26",
    "52.215.127.0/24",
    # Europe - Frankfurt
    "35.156.191.128/25",
    # Asia Pacific - Singapore
    "54.169.127.128/26",
    # Asia Pacific - Tokyo
    "54.65.63.192/26",
    # Asia Pacific - Sydney
    "54.252.254.64/26",
    # South America - Sao Paulo
    "177.71.206.192/26",
    # Twilio Edge locations
    "168.86.128.0/18",
]

# Etisalat CPaaS IP ranges (placeholder - get actual ranges from e& enterprise)
# These should be obtained from Etisalat's documentation or support
ETISALAT_IP_RANGES = [
    # UAE Data Centers (placeholder ranges - replace with actual)
    "185.56.96.0/22",
    "91.74.0.0/16",
    # Add actual Etisalat CPaaS IP ranges here
]

# Development/Testing IPs - Add your IPs here for local testing
DEV_ALLOWED_IPS = [
    "217.164.6.153/32",  # Azam's IPv4
    "2001:8f8:1761:8bc:9df3:910d:3c3a:eba2/128",  # Azam's IPv6
]

# Combined ranges for when provider is unknown
ALL_VOICE_PROVIDER_IPS = TWILIO_IP_RANGES + ETISALAT_IP_RANGES + DEV_ALLOWED_IPS


def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP from request, handling proxies.

    Checks X-Forwarded-For header first (for reverse proxy setups),
    then falls back to direct client IP.
    """
    # Check X-Forwarded-For header (common with reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, first one is the client
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return ""


def is_ip_in_ranges(ip: str, ip_ranges: List[str]) -> bool:
    """
    Check if an IP address is within any of the given CIDR ranges.

    Args:
        ip: IP address to check
        ip_ranges: List of CIDR notation IP ranges

    Returns:
        True if IP is in any of the ranges, False otherwise
    """
    try:
        ip_addr = ipaddress.ip_address(ip)
        for ip_range in ip_ranges:
            try:
                network = ipaddress.ip_network(ip_range, strict=False)
                if ip_addr in network:
                    return True
            except ValueError:
                logger.warning(f"Invalid IP range in whitelist: {ip_range}")
                continue
        return False
    except ValueError:
        logger.warning(f"Invalid IP address: {ip}")
        return False


def validate_ip_whitelist(
    request: Request,
    provider: str = "all",
    allow_localhost: bool = True,
) -> Tuple[bool, str]:
    """
    Validate that the request comes from a whitelisted IP.

    Args:
        request: FastAPI request object
        provider: 'twilio', 'etisalat', or 'all'
        allow_localhost: Whether to allow localhost (for development)

    Returns:
        Tuple of (is_valid, client_ip)
    """
    import os

    client_ip = get_client_ip(request)

    if not client_ip:
        return False, ""

    # Allow all IPs in development mode (DEBUG=true or VOICE_WEBHOOK_ALLOW_ALL=true)
    if os.getenv("DEBUG", "").lower() == "true" or os.getenv("VOICE_WEBHOOK_ALLOW_ALL", "").lower() == "true":
        logger.debug(f"DEBUG mode - allowing all IPs: {client_ip}")
        return True, client_ip

    # Allow localhost for development
    if allow_localhost and client_ip in ["127.0.0.1", "::1", "localhost"]:
        logger.debug(f"Allowing localhost IP: {client_ip}")
        return True, client_ip

    # Select IP ranges based on provider
    if provider == "twilio":
        ip_ranges = TWILIO_IP_RANGES
    elif provider == "etisalat":
        ip_ranges = ETISALAT_IP_RANGES
    else:
        ip_ranges = ALL_VOICE_PROVIDER_IPS

    is_valid = is_ip_in_ranges(client_ip, ip_ranges)

    if not is_valid:
        logger.warning(
            f"Voice webhook request from non-whitelisted IP: {client_ip} "
            f"(provider: {provider})"
        )

    return is_valid, client_ip


def parse_basic_auth(authorization_header: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse Basic Auth credentials from Authorization header.

    Args:
        authorization_header: The Authorization header value

    Returns:
        Tuple of (username, password) or (None, None) if invalid
    """
    if not authorization_header:
        return None, None

    if not authorization_header.startswith("Basic "):
        return None, None

    try:
        # Extract base64 encoded credentials
        encoded_credentials = authorization_header[6:]  # Remove "Basic " prefix
        decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")

        # Split into username and password
        if ":" not in decoded_credentials:
            return None, None

        username, password = decoded_credentials.split(":", 1)
        return username, password
    except Exception as e:
        logger.warning(f"Failed to parse Basic Auth header: {e}")
        return None, None


def validate_basic_auth(
    request: Request,
    expected_username: str,
    expected_password: str,
) -> bool:
    """
    Validate Basic Auth credentials from request.

    Args:
        request: FastAPI request object
        expected_username: Expected username
        expected_password: Expected password

    Returns:
        True if credentials match, False otherwise
    """
    auth_header = request.headers.get("Authorization")
    username, password = parse_basic_auth(auth_header)

    if not username or not password:
        return False

    # Use constant-time comparison to prevent timing attacks
    username_match = secrets.compare_digest(username, expected_username)
    password_match = secrets.compare_digest(password, expected_password)

    return username_match and password_match


def generate_basic_auth_credentials() -> Tuple[str, str]:
    """
    Generate secure random Basic Auth credentials.

    Returns:
        Tuple of (username, password)
    """
    username = f"webhook_{secrets.token_hex(8)}"
    password = secrets.token_urlsafe(32)
    return username, password


def build_webhook_url_with_auth(
    base_url: str,
    username: str,
    password: str,
) -> str:
    """
    Build a webhook URL with Basic Auth credentials embedded.

    This format is supported by Twilio and most webhook providers:
    https://username:password@example.com/webhook

    Args:
        base_url: The base webhook URL (e.g., https://example.com/webhook)
        username: Basic Auth username
        password: Basic Auth password

    Returns:
        URL with embedded credentials
    """
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(base_url)

    # Build URL with credentials
    netloc_with_auth = f"{username}:{password}@{parsed.netloc}"

    authenticated_url = urlunparse((
        parsed.scheme,
        netloc_with_auth,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment,
    ))

    return authenticated_url


async def verify_webhook_security(
    request: Request,
    provider: str,
    deployment_config: dict,
    enable_ip_whitelist: bool = True,
    enable_basic_auth: bool = True,
    allow_localhost: bool = True,
) -> None:
    """
    Comprehensive webhook security verification.

    Performs IP whitelisting and Basic Auth validation based on configuration.

    Args:
        request: FastAPI request object
        provider: Voice provider ('twilio' or 'etisalat')
        deployment_config: Deployment configuration containing auth settings
        enable_ip_whitelist: Whether to enforce IP whitelisting
        enable_basic_auth: Whether to enforce Basic Auth
        allow_localhost: Whether to allow localhost (for development)

    Raises:
        HTTPException: If security validation fails
    """
    client_ip = get_client_ip(request)

    # IP Whitelist validation
    if enable_ip_whitelist:
        is_valid_ip, _ = validate_ip_whitelist(
            request,
            provider=provider,
            allow_localhost=allow_localhost,
        )

        if not is_valid_ip:
            logger.warning(
                f"Webhook rejected - IP not whitelisted: {client_ip} "
                f"(provider: {provider})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request origin not authorized",
            )

    # Basic Auth validation
    if enable_basic_auth:
        webhook_username = deployment_config.get("webhook_username")
        webhook_password = deployment_config.get("webhook_password")

        # Only validate if credentials are configured
        if webhook_username and webhook_password:
            if not validate_basic_auth(request, webhook_username, webhook_password):
                logger.warning(
                    f"Webhook rejected - Basic Auth failed: {client_ip} "
                    f"(provider: {provider})"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Basic"},
                )

    logger.debug(f"Webhook security verified: {client_ip} (provider: {provider})")
