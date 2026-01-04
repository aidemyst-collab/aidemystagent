"""
WhatsApp Webhook API Endpoints

Handles incoming WhatsApp messages and webhook verification.
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Request, Response, HTTPException, Query, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.services.whatsapp_provider import (
    WhatsAppClient,
    WhatsAppError,
    verify_webhook_challenge,
    validate_webhook_signature,
    IncomingMessage,
    MessageType,
)
from app.services.whatsapp_provider.message_types import WebhookPayload
from app.models.credential import Credential, CredentialProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])


# In-memory session storage (replace with Redis in production)
whatsapp_sessions: Dict[str, Dict[str, Any]] = {}


@router.get("/webhook")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """
    Webhook verification endpoint for Meta.

    When you configure a webhook URL in the Meta Developer Dashboard,
    Meta sends a GET request to verify ownership of the endpoint.

    Query Parameters:
        hub.mode: Should be "subscribe"
        hub.verify_token: Must match your configured verify token
        hub.challenge: Random string to echo back

    Returns:
        The challenge string if verification succeeds
        403 error if verification fails
    """
    # Get verify token from settings or use a default for testing
    verify_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", "agentstudio_whatsapp_verify")

    success, challenge = verify_webhook_challenge(
        mode=hub_mode,
        token=hub_token,
        challenge=hub_challenge,
        verify_token=verify_token,
    )

    if success:
        logger.info("WhatsApp webhook verified successfully")
        return PlainTextResponse(content=challenge)

    logger.warning("WhatsApp webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def handle_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle incoming WhatsApp webhook events.

    This endpoint receives:
    - Incoming messages from users
    - Message status updates (sent, delivered, read)
    - Other notification types

    The payload is signed with HMAC-SHA256 using your app secret.
    We validate this signature before processing.

    Returns:
        200 OK to acknowledge receipt (Meta expects this)
    """
    # Get raw payload for signature validation
    payload = await request.body()

    # Get signature header
    signature = request.headers.get("X-Hub-Signature-256")

    # Get app secret from settings (can also be per-credential)
    app_secret = getattr(settings, "WHATSAPP_APP_SECRET", None)

    # Validate signature if app secret is configured
    if app_secret and signature:
        if not validate_webhook_signature(payload, signature, app_secret):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse the webhook payload
    try:
        data = json.loads(payload)
        webhook_payload = WebhookPayload(**data)
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        # Still return 200 to prevent Meta from retrying
        return Response(status_code=200)

    # Process messages
    messages = webhook_payload.get_messages()
    for message in messages:
        await process_incoming_message(message, db)

    # Process status updates
    statuses = webhook_payload.get_statuses()
    for status in statuses:
        logger.info(
            f"Message {status.id} status: {status.status} "
            f"for {status.recipient_id}"
        )

    # Always return 200 to acknowledge receipt
    return Response(status_code=200)


async def process_incoming_message(
    message: IncomingMessage,
    db: AsyncSession,
) -> None:
    """
    Process an incoming WhatsApp message.

    This function:
    1. Logs the message
    2. Updates session state
    3. Triggers agent execution if configured
    4. Sends response back to user

    Args:
        message: Parsed incoming message
        db: Database session
    """
    logger.info(
        f"Received {message.message_type.value} message from {message.from_number}: "
        f"{message.message_id}"
    )

    # Get or create session for this user
    session_key = f"whatsapp:{message.from_number}"
    session = whatsapp_sessions.get(session_key, {
        "created_at": datetime.utcnow(),
        "last_message_at": None,
        "message_count": 0,
        "context": {},
    })

    session["last_message_at"] = datetime.utcnow()
    session["message_count"] += 1
    whatsapp_sessions[session_key] = session

    # Extract message content based on type
    user_input = ""
    if message.message_type == MessageType.TEXT and message.text:
        user_input = message.text.body
    elif message.message_type == MessageType.INTERACTIVE and message.interactive:
        if message.interactive.button_reply:
            user_input = message.interactive.button_reply.title
        elif message.interactive.list_reply:
            user_input = message.interactive.list_reply.title
    elif message.message_type == MessageType.BUTTON and message.button:
        user_input = message.button.title

    if user_input:
        logger.info(f"User input: {user_input}")

        # TODO: Trigger agent execution based on configured workflow
        # For now, just log the message
        # The actual agent execution will be implemented when integrating
        # with the LangGraph engine

    # Handle media messages
    if message.media:
        logger.info(
            f"Received {message.media.media_type} media: {message.media.media_id}"
        )


@router.post("/send/{credential_id}")
async def send_message(
    credential_id: str,
    to: str,
    message_type: str,
    content: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    """
    Send a WhatsApp message using stored credentials.

    This endpoint is used by agent workflows to send messages.

    Args:
        credential_id: ID of the WhatsApp credential to use
        to: Recipient phone number (with country code)
        message_type: Type of message (text, template, media, interactive)
        content: Message content (varies by type)

    Returns:
        API response with message ID
    """
    # Get credential from database
    from sqlalchemy import select
    result = await db.execute(
        select(Credential).where(
            Credential.id == credential_id,
            Credential.provider == CredentialProvider.WHATSAPP_META,
            Credential.is_active == "active",
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(status_code=404, detail="WhatsApp credential not found")

    # Parse connection config from api_key field (stored as JSON)
    try:
        config = json.loads(credential.api_key)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid credential configuration")

    phone_number_id = config.get("phone_number_id")
    access_token = config.get("access_token")
    business_account_id = config.get("business_account_id")

    if not phone_number_id or not access_token:
        raise HTTPException(status_code=500, detail="Missing WhatsApp credentials")

    # Create client
    client = WhatsAppClient(
        phone_number_id=phone_number_id,
        access_token=access_token,
        business_account_id=business_account_id,
    )

    try:
        # Send message based on type
        if message_type == "text":
            response = await client.send_text_message(
                to=to,
                text=content.get("body", ""),
                preview_url=content.get("preview_url", False),
            )

        elif message_type == "template":
            response = await client.send_template_message(
                to=to,
                template_name=content.get("template_name", ""),
                language_code=content.get("language_code", "en"),
                components=content.get("components"),
            )

        elif message_type == "media":
            response = await client.send_media_message(
                to=to,
                media_type=content.get("media_type", "image"),
                media_url=content.get("media_url"),
                media_id=content.get("media_id"),
                caption=content.get("caption"),
                filename=content.get("filename"),
            )

        elif message_type == "interactive":
            response = await client.send_interactive_message(
                to=to,
                interactive_type=content.get("interactive_type", "button"),
                body_text=content.get("body", ""),
                action=content.get("action", {}),
                header=content.get("header"),
                footer=content.get("footer"),
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported message type: {message_type}"
            )

        # Update last used timestamp
        credential.last_used_at = datetime.utcnow()
        await db.commit()

        return response

    except WhatsAppError as e:
        logger.error(f"WhatsApp API error: {e.message} (code: {e.error_code})")
        raise HTTPException(
            status_code=500,
            detail=f"WhatsApp API error: {e.message}"
        )


@router.get("/templates/{credential_id}")
async def get_templates(
    credential_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get available message templates for a WhatsApp Business account.

    Templates must be pre-approved by Meta and are required for
    sending messages outside the 24-hour customer service window.

    Args:
        credential_id: ID of the WhatsApp credential

    Returns:
        List of available templates
    """
    from sqlalchemy import select
    result = await db.execute(
        select(Credential).where(
            Credential.id == credential_id,
            Credential.provider == CredentialProvider.WHATSAPP_META,
            Credential.is_active == "active",
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(status_code=404, detail="WhatsApp credential not found")

    try:
        config = json.loads(credential.api_key)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid credential configuration")

    phone_number_id = config.get("phone_number_id")
    access_token = config.get("access_token")
    business_account_id = config.get("business_account_id")

    if not business_account_id:
        raise HTTPException(
            status_code=400,
            detail="Business Account ID required for template management"
        )

    client = WhatsAppClient(
        phone_number_id=phone_number_id,
        access_token=access_token,
        business_account_id=business_account_id,
    )

    try:
        templates = await client.get_templates()
        return {"templates": templates}
    except WhatsAppError as e:
        raise HTTPException(status_code=500, detail=str(e.message))


@router.post("/mark-read/{credential_id}")
async def mark_message_read(
    credential_id: str,
    message_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a message as read.

    This shows blue checkmarks to the sender.

    Args:
        credential_id: ID of the WhatsApp credential
        message_id: ID of the message to mark as read

    Returns:
        Success response
    """
    from sqlalchemy import select
    result = await db.execute(
        select(Credential).where(
            Credential.id == credential_id,
            Credential.provider == CredentialProvider.WHATSAPP_META,
            Credential.is_active == "active",
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(status_code=404, detail="WhatsApp credential not found")

    try:
        config = json.loads(credential.api_key)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid credential configuration")

    client = WhatsAppClient(
        phone_number_id=config.get("phone_number_id"),
        access_token=config.get("access_token"),
    )

    try:
        await client.mark_as_read(message_id)
        return {"success": True, "message": "Message marked as read"}
    except WhatsAppError as e:
        raise HTTPException(status_code=500, detail=str(e.message))
