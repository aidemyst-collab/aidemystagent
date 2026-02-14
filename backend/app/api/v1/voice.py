"""
Voice Webhook API Endpoints

Handles incoming voice calls and recording callbacks from Twilio and Etisalat.

Security Features:
- IP Whitelisting: Only accepts requests from Twilio/Etisalat IP ranges
- Basic Auth: Optional basic auth for webhook URLs
- Webhook Signature: Provider-specific signature validation
- API Key: Deployment-specific API key validation
"""

import uuid
import base64
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Header
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.redis_client import get_redis, get_redis_binary
from app.core.config import settings
from app.models.deployment import Deployment
from app.models.credential import Credential
from app.services.voice_providers import (
    get_voice_provider,
    VoiceProviderError,
    verify_webhook_security,
    get_client_ip,
)
from app.services.langgraph_engine import LangGraphEngine


def get_original_base_url(request: Request) -> str:
    """
    Reconstruct the original base URL from forwarded headers.

    When behind a reverse proxy, request.base_url returns the internal URL.
    We need the external URL for callback URLs that Twilio will call.
    """
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    forwarded_host = request.headers.get("x-forwarded-host", request.url.netloc)
    return f"{forwarded_proto}://{forwarded_host}/"


def get_original_url(request: Request) -> str:
    """
    Reconstruct the original URL that Twilio signed.

    When behind a reverse proxy, request.url returns the internal URL.
    Twilio signs the external URL, so we must reconstruct it from
    X-Forwarded-* headers.
    """
    # Get forwarded headers (set by nginx/proxy)
    forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    forwarded_host = request.headers.get("x-forwarded-host", request.url.netloc)

    # Reconstruct the URL with original scheme and host
    original_url = f"{forwarded_proto}://{forwarded_host}{request.url.path}"

    # Include query string if present
    if request.url.query:
        original_url += f"?{request.url.query}"

    return original_url

logger = logging.getLogger(__name__)

router = APIRouter()

# Session TTL in seconds (10 minutes)
VOICE_SESSION_TTL = 600


async def get_deployment_and_credential(
    deployment_id: str,
    api_key: str,
    db: AsyncSession,
) -> tuple:
    """
    Validate deployment and get associated voice credential.

    Returns:
        Tuple of (deployment, credential, provider_name)
    """
    # Validate deployment (eagerly load agent to avoid async lazy loading issues)
    result = await db.execute(
        select(Deployment)
        .options(selectinload(Deployment.agent))
        .where(
            Deployment.id == deployment_id,
            Deployment.api_key == api_key,
            Deployment.status == "active",
        )
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found or invalid API key",
        )

    # Get agent config to find voice node settings
    agent_config = deployment.agent.config if deployment.agent else {}
    nodes = agent_config.get("nodes", [])

    # Find VOICE_INPUT node
    # Node structure: { type: "VoiceInputNode", data: { type: "VOICE_INPUT", config: {...} } }
    voice_input_node = None
    for node in nodes:
        node_data = node.get("data", {})
        # Check both node.type and node.data.type for compatibility
        if node.get("type") == "VOICE_INPUT" or node_data.get("type") == "VOICE_INPUT":
            voice_input_node = node_data
            break

    if not voice_input_node:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deployment does not have a VOICE_INPUT node",
        )

    # Config can be at voice_input_node.config or directly in voice_input_node
    voice_config = voice_input_node.get("config", voice_input_node)
    provider_name = voice_config.get("provider", "twilio")
    credential_id = voice_config.get("credentialId")

    if not credential_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="VOICE_INPUT node missing credential configuration",
        )

    # Get credential
    result = await db.execute(
        select(Credential).where(
            Credential.id == credential_id,
            Credential.organization_id == deployment.organization_id,
        )
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice credential not found",
        )

    return deployment, credential, provider_name, voice_input_node


@router.post("/webhook/incoming/{deployment_id}")
async def handle_incoming_call(
    deployment_id: str,
    request: Request,
    api_key: str,
    db: AsyncSession = Depends(get_db),
    x_twilio_signature: Optional[str] = Header(None),
    x_etisalat_signature: Optional[str] = Header(None),
):
    """
    Handle incoming voice call webhook.

    This endpoint is called by Twilio or Etisalat when a call comes in.
    It validates the deployment, plays a greeting, and starts recording.

    Security layers:
    1. API Key validation (via query parameter)
    2. IP Whitelisting (Twilio/Etisalat IP ranges)
    3. Basic Auth (optional, if configured)
    4. Webhook Signature validation (provider-specific)
    """
    try:
        # Parse request data based on content type
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            request_data = await request.json()
        else:
            # Form data (Twilio uses this)
            form_data = await request.form()
            request_data = dict(form_data)

        # Get deployment and credential
        deployment, credential, provider_name, voice_config = await get_deployment_and_credential(
            deployment_id, api_key, db
        )

        # Get deployment config for security settings
        deployment_config = deployment.config or {}
        webhook_config = deployment_config.get("webhook_security", {})

        # Security Layer 2 & 3: IP Whitelisting and Basic Auth
        # Check if security is enabled (default: enabled in production, disabled in development)
        enable_ip_whitelist = webhook_config.get(
            "enable_ip_whitelist",
            getattr(settings, "VOICE_WEBHOOK_IP_WHITELIST", True)
        )
        enable_basic_auth = webhook_config.get(
            "enable_basic_auth",
            getattr(settings, "VOICE_WEBHOOK_BASIC_AUTH", False)
        )
        allow_localhost = getattr(settings, "DEBUG", False)

        await verify_webhook_security(
            request=request,
            provider=provider_name,
            deployment_config=webhook_config,
            enable_ip_whitelist=enable_ip_whitelist,
            enable_basic_auth=enable_basic_auth,
            allow_localhost=allow_localhost,
        )

        # Initialize voice provider
        try:
            provider = get_voice_provider(provider_name, credential.decrypted_value)
        except VoiceProviderError as e:
            logger.error(f"Voice provider error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e),
            )

        # Security Layer 4: Validate webhook signature
        signature = x_twilio_signature or x_etisalat_signature or ""
        request_url = get_original_url(request)

        if signature and not provider.validate_webhook_signature(
            request_url, request_data, signature
        ):
            logger.warning(f"Invalid webhook signature for deployment {deployment_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )

        # Parse incoming call data
        call_data = provider.parse_incoming_call(request_data)

        # Create session ID for this call
        session_id = str(uuid.uuid4())

        # Store session data in Redis
        redis = await get_redis()
        session_data = {
            "deployment_id": deployment_id,
            "call_sid": call_data["call_sid"],
            "caller_id": call_data["caller_id"],
            "provider": provider_name,
            "created_at": datetime.utcnow().isoformat(),
            "turn_count": 0,
        }
        await redis.setex(
            f"voice_session:{session_id}",
            VOICE_SESSION_TTL,
            str(session_data),
        )

        # Generate greeting response
        base_url = get_original_base_url(request)
        recording_callback_url = (
            f"{base_url}api/v1/voice/webhook/recording/{deployment_id}"
            f"?api_key={api_key}&session_id={session_id}"
        )

        response = provider.generate_greeting_response(
            greeting=voice_config.get("greeting", "Hello! How can I help you?"),
            recording_callback_url=recording_callback_url,
            language=voice_config.get("language", "en-US"),
            max_duration=voice_config.get("maxDuration", 60),
            play_beep=voice_config.get("playBeep", True),
        )

        logger.info(
            f"Incoming call handled: deployment={deployment_id}, "
            f"caller={call_data['caller_id']}, session={session_id}"
        )

        return Response(
            content=response.content,
            media_type=response.content_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error handling incoming call: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to handle incoming call",
        )


@router.post("/webhook/recording/{deployment_id}")
async def handle_recording_complete(
    deployment_id: str,
    request: Request,
    api_key: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle recording complete webhook.

    This endpoint is called when the caller finishes speaking.
    It fetches the recording, runs the workflow, and returns the response.

    Security layers (same as incoming call):
    1. API Key validation (via query parameter)
    2. IP Whitelisting (Twilio/Etisalat IP ranges)
    3. Basic Auth (optional, if configured)
    """
    try:
        # Parse request data
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            request_data = await request.json()
        else:
            form_data = await request.form()
            request_data = dict(form_data)

        # Get deployment and credential
        deployment, credential, provider_name, voice_config = await get_deployment_and_credential(
            deployment_id, api_key, db
        )

        # Get deployment config for security settings
        deployment_config = deployment.config or {}
        webhook_config = deployment_config.get("webhook_security", {})

        # Security: IP Whitelisting and Basic Auth
        enable_ip_whitelist = webhook_config.get(
            "enable_ip_whitelist",
            getattr(settings, "VOICE_WEBHOOK_IP_WHITELIST", True)
        )
        enable_basic_auth = webhook_config.get(
            "enable_basic_auth",
            getattr(settings, "VOICE_WEBHOOK_BASIC_AUTH", False)
        )
        allow_localhost = getattr(settings, "DEBUG", False)

        await verify_webhook_security(
            request=request,
            provider=provider_name,
            deployment_config=webhook_config,
            enable_ip_whitelist=enable_ip_whitelist,
            enable_basic_auth=enable_basic_auth,
            allow_localhost=allow_localhost,
        )

        # Initialize voice provider
        provider = get_voice_provider(provider_name, credential.decrypted_value)

        # Parse recording data
        recording_data = provider.parse_recording_complete(request_data)

        # Fetch the recording audio
        try:
            audio_data = await provider.fetch_recording(recording_data["recording_url"])
        except VoiceProviderError as e:
            logger.error(f"Failed to fetch recording: {e}")
            # Return error message to caller
            response = provider.generate_text_response(
                text="Sorry, I couldn't hear you. Please try again.",
                after_action="hangup",
            )
            return Response(
                content=response.content,
                media_type=response.content_type,
            )

        # Get session data from Redis
        redis = await get_redis()
        session_key = f"voice_session:{session_id}"
        session_raw = await redis.get(session_key)

        if not session_raw:
            logger.warning(f"Session not found: {session_id}")
            response = provider.generate_hangup_response(
                goodbye_message="Session expired. Please call again.",
            )
            return Response(
                content=response.content,
                media_type=response.content_type,
            )

        # Execute the workflow with audio input
        try:
            engine = LangGraphEngine(db=db, redis_client=await get_redis())

            # Prepare input for workflow
            user_input = {
                "audio_data": base64.b64encode(audio_data.audio_data).decode("utf-8"),
                "audio_format": audio_data.audio_format,
                "caller_id": recording_data.get("call_sid", ""),
                "provider": provider_name,
            }

            # Execute workflow
            result = await engine.execute_agent(
                agent_config=deployment.agent.config,
                user_input=user_input,
                input_mode="audio",
                session_id=session_id,
                organization_id=str(deployment.organization_id),
                workflow_id=str(deployment.agent_id),
            )

            # Get output audio or text from result
            voice_output = result.get("voice_output", {})
            output_audio = result.get("output_audio") or result.get("audio_data")

        except Exception as e:
            logger.exception(f"Workflow execution failed: {e}")
            response = provider.generate_text_response(
                text="Sorry, I encountered an error processing your request.",
                after_action="hangup",
            )
            return Response(
                content=response.content,
                media_type=response.content_type,
            )

        # Find VOICE_OUTPUT node config
        nodes = deployment.agent.config.get("nodes", [])
        voice_output_config = {}
        for node in nodes:
            node_data = node.get("data", {})
            # Check both node.type and node.data.type for compatibility
            if node.get("type") == "VOICE_OUTPUT" or node_data.get("type") == "VOICE_OUTPUT":
                voice_output_config = node_data
                break

        after_action = voice_output_config.get("afterResponse", "hangup")

        # Generate appropriate response
        if output_audio:
            # Store audio temporarily and get URL (use binary redis for audio data)
            audio_id = str(uuid.uuid4())
            redis_binary = await get_redis_binary()
            await redis_binary.setex(
                f"voice_audio:{audio_id}",
                300,  # 5 minutes TTL
                output_audio if isinstance(output_audio, bytes) else base64.b64decode(output_audio),
            )

            base_url = get_original_base_url(request)
            audio_url = f"{base_url}api/v1/voice/audio/{audio_id}"

            if after_action == "continue":
                # Build recording callback URL for continue action
                recording_callback_url = (
                    f"{base_url}api/v1/voice/webhook/recording/{deployment_id}"
                    f"?api_key={api_key}&session_id={session_id}"
                )
                # Play audio then continue recording
                response = provider.generate_audio_response(
                    audio_url=audio_url,
                    after_action="continue",
                    recording_callback_url=recording_callback_url,
                    max_duration=voice_config.get("config", {}).get("maxDuration", 60),
                )
            else:
                response = provider.generate_audio_response(
                    audio_url=audio_url,
                    after_action=after_action,
                    transfer_to=voice_output_config.get("transferTo"),
                )
        else:
            # Fallback to text response
            fallback_text = voice_output_config.get(
                "fallbackMessage",
                "I'm sorry, I don't have a response for that.",
            )
            response = provider.generate_text_response(
                text=fallback_text,
                after_action=after_action,
            )

        # Update session turn count
        session_data = eval(session_raw)  # Safe since we wrote it
        session_data["turn_count"] = session_data.get("turn_count", 0) + 1
        await redis.setex(session_key, VOICE_SESSION_TTL, str(session_data))

        logger.info(
            f"Recording processed: deployment={deployment_id}, "
            f"session={session_id}, turn={session_data['turn_count']}"
        )

        return Response(
            content=response.content,
            media_type=response.content_type,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error handling recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process recording",
        )


@router.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """
    Serve stored audio file.

    Audio files are stored temporarily in Redis for playback.
    """
    redis = await get_redis_binary()
    audio_data = await redis.get(f"voice_audio:{audio_id}")

    if not audio_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio not found or expired",
        )

    return Response(
        content=audio_data,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename={audio_id}.mp3",
        },
    )
