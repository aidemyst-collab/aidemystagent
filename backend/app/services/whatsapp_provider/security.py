"""
WhatsApp Webhook Security

Handles webhook verification and payload validation.
"""

import hmac
import hashlib
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def verify_webhook_challenge(
    mode: Optional[str],
    token: Optional[str],
    challenge: Optional[str],
    verify_token: str,
) -> Tuple[bool, Optional[str]]:
    """
    Verify the webhook challenge from Meta.

    When setting up the webhook, Meta sends a GET request with:
    - hub.mode: Should be "subscribe"
    - hub.verify_token: Should match your configured token
    - hub.challenge: Random string to echo back

    Args:
        mode: The hub.mode parameter
        token: The hub.verify_token parameter
        challenge: The hub.challenge parameter
        verify_token: Your configured verification token

    Returns:
        Tuple of (success, challenge_to_return)
        If success is True, return the challenge string
        If success is False, challenge_to_return will be None

    Example:
        @app.get("/webhook/whatsapp")
        async def verify_webhook(
            hub_mode: str = Query(None, alias="hub.mode"),
            hub_token: str = Query(None, alias="hub.verify_token"),
            hub_challenge: str = Query(None, alias="hub.challenge"),
        ):
            success, response = verify_webhook_challenge(
                hub_mode, hub_token, hub_challenge, settings.WHATSAPP_VERIFY_TOKEN
            )
            if success:
                return PlainTextResponse(response)
            raise HTTPException(status_code=403, detail="Verification failed")
    """
    if not all([mode, token, challenge]):
        logger.warning("Missing webhook verification parameters")
        return False, None

    if mode != "subscribe":
        logger.warning(f"Invalid hub.mode: {mode}")
        return False, None

    if token != verify_token:
        logger.warning("Verify token mismatch")
        return False, None

    logger.info("Webhook verification successful")
    return True, challenge


def validate_webhook_signature(
    payload: bytes,
    signature_header: Optional[str],
    app_secret: str,
) -> bool:
    """
    Validate the webhook payload signature.

    Meta signs all webhook payloads using HMAC-SHA256 with your app secret.
    The signature is sent in the X-Hub-Signature-256 header.

    Args:
        payload: Raw request body bytes
        signature_header: Value of X-Hub-Signature-256 header
        app_secret: Your WhatsApp App Secret from Meta Developer Dashboard

    Returns:
        True if signature is valid, False otherwise

    Example:
        @app.post("/webhook/whatsapp")
        async def handle_webhook(request: Request):
            payload = await request.body()
            signature = request.headers.get("X-Hub-Signature-256")

            if not validate_webhook_signature(payload, signature, app_secret):
                raise HTTPException(status_code=401, detail="Invalid signature")

            # Process the webhook...
    """
    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header")
        return False

    if not signature_header.startswith("sha256="):
        logger.warning(f"Invalid signature format: {signature_header[:20]}")
        return False

    expected_signature = signature_header[7:]  # Remove "sha256=" prefix

    # Calculate HMAC-SHA256
    computed_signature = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    is_valid = hmac.compare_digest(expected_signature, computed_signature)

    if not is_valid:
        logger.warning("Webhook signature validation failed")
    else:
        logger.debug("Webhook signature validated successfully")

    return is_valid


def generate_verify_token(length: int = 32) -> str:
    """
    Generate a secure random verification token.

    This token should be stored securely and configured in:
    1. Your application settings
    2. Meta Developer Dashboard webhook configuration

    Args:
        length: Length of the token (default 32 characters)

    Returns:
        Secure random hex string
    """
    import secrets
    return secrets.token_hex(length // 2)


class WebhookValidator:
    """
    Stateful webhook validator for managing multiple WhatsApp accounts.

    Use this class when you need to handle webhooks for multiple
    WhatsApp Business accounts with different secrets.
    """

    def __init__(self):
        self._accounts: dict[str, dict] = {}

    def register_account(
        self,
        phone_number_id: str,
        verify_token: str,
        app_secret: str,
    ) -> None:
        """
        Register a WhatsApp Business account for webhook validation.

        Args:
            phone_number_id: The Phone Number ID from Meta
            verify_token: Verification token for this account
            app_secret: App secret for signature validation
        """
        self._accounts[phone_number_id] = {
            "verify_token": verify_token,
            "app_secret": app_secret,
        }
        logger.info(f"Registered WhatsApp account: {phone_number_id}")

    def unregister_account(self, phone_number_id: str) -> None:
        """Remove a registered account."""
        if phone_number_id in self._accounts:
            del self._accounts[phone_number_id]
            logger.info(f"Unregistered WhatsApp account: {phone_number_id}")

    def get_verify_token(self, phone_number_id: str) -> Optional[str]:
        """Get the verify token for an account."""
        account = self._accounts.get(phone_number_id)
        return account["verify_token"] if account else None

    def validate_for_account(
        self,
        phone_number_id: str,
        payload: bytes,
        signature_header: Optional[str],
    ) -> bool:
        """
        Validate webhook signature for a specific account.

        Args:
            phone_number_id: The Phone Number ID
            payload: Raw request body
            signature_header: X-Hub-Signature-256 header value

        Returns:
            True if valid, False otherwise
        """
        account = self._accounts.get(phone_number_id)
        if not account:
            logger.warning(f"Unknown phone number ID: {phone_number_id}")
            return False

        return validate_webhook_signature(
            payload, signature_header, account["app_secret"]
        )


# Singleton instance for multi-account webhook validation
webhook_validator = WebhookValidator()
