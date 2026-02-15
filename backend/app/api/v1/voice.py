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
import json
import asyncio
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Header, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db, AsyncSessionLocal
from app.core.redis_client import get_redis, get_redis_binary
from app.core.config import settings
from app.models.deployment import Deployment
from app.models.credential import Credential
from app.models.agent import Agent
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

# Voice job TTL in seconds (10 minutes - same as session)
VOICE_JOB_TTL = 600

# Max status check iterations before giving up
MAX_STATUS_CHECKS = 30

# Job status constants
JOB_STATUS_PROCESSING = "processing"
JOB_STATUS_COMPLETE = "complete"
JOB_STATUS_FAILED = "failed"


async def process_voice_workflow_background(
    job_id: str,
    deployment_id: str,
    agent_config: dict,
    recording_url: str,
    session_id: str,
    organization_id: str,
    agent_id: str,
    provider_name: str,
    credentials: dict,
    voice_output_config: dict,
):
    """
    Background task to process voice workflow.

    This runs asynchronously after returning TwiML to Twilio,
    allowing us to exceed the 15-second webhook timeout.
    """
    try:
        logger.info(f"Background job {job_id}: Starting voice workflow processing")

        # Get Redis client
        redis = await get_redis()
        redis_binary = await get_redis_binary()

        # Initialize voice provider
        provider = get_voice_provider(provider_name, credentials)

        # Fetch the recording audio
        try:
            audio_data = await provider.fetch_recording(recording_url)
            logger.info(f"Background job {job_id}: Fetched recording ({len(audio_data.audio_data)} bytes)")
        except VoiceProviderError as e:
            logger.error(f"Background job {job_id}: Failed to fetch recording: {e}")
            await redis.setex(
                f"voice_job:{job_id}",
                VOICE_JOB_TTL,
                json.dumps({
                    "status": JOB_STATUS_FAILED,
                    "error": "Failed to fetch recording",
                    "error_message": "Sorry, I couldn't hear you. Please try again.",
                })
            )
            return

        # Execute the workflow
        try:
            # Create a new database session for background task
            async with AsyncSessionLocal() as db:
                engine = LangGraphEngine(db=db, redis_client=redis)

                # Prepare input for workflow
                user_input = {
                    "audio_data": base64.b64encode(audio_data.audio_data).decode("utf-8"),
                    "audio_format": audio_data.audio_format,
                    "caller_id": session_id,
                    "provider": provider_name,
                }

                # Execute workflow
                logger.info(f"Background job {job_id}: Executing agent workflow")
                result = await engine.execute_agent(
                    agent_config=agent_config,
                    user_input=user_input,
                    input_mode="audio",
                    session_id=session_id,
                    organization_id=organization_id,
                    workflow_id=agent_id,
                )

                logger.info(f"Background job {job_id}: Workflow execution complete")

                # Get output audio or text from result
                output_audio = result.get("output_audio") or result.get("audio_data")
                output_text = result.get("response") or result.get("output") or ""

        except Exception as e:
            logger.exception(f"Background job {job_id}: Workflow execution failed: {e}")
            await redis.setex(
                f"voice_job:{job_id}",
                VOICE_JOB_TTL,
                json.dumps({
                    "status": JOB_STATUS_FAILED,
                    "error": "Workflow execution failed",
                    "error_message": "Sorry, I encountered an error processing your request.",
                })
            )
            return

        # Store result
        result_data = {
            "status": JOB_STATUS_COMPLETE,
            "voice_output_config": voice_output_config,
        }

        if output_audio:
            # Store audio in binary Redis
            audio_id = str(uuid.uuid4())
            audio_bytes = output_audio if isinstance(output_audio, bytes) else base64.b64decode(output_audio)
            await redis_binary.setex(
                f"voice_audio:{audio_id}",
                VOICE_JOB_TTL,
                audio_bytes,
            )
            result_data["audio_id"] = audio_id
            logger.info(f"Background job {job_id}: Stored audio response ({len(audio_bytes)} bytes)")
        elif output_text:
            result_data["text_response"] = output_text
            logger.info(f"Background job {job_id}: Text response: {output_text[:100]}...")
        else:
            result_data["text_response"] = voice_output_config.get(
                "fallbackMessage",
                "I'm sorry, I don't have a response for that."
            )

        # Save job result
        await redis.setex(
            f"voice_job:{job_id}",
            VOICE_JOB_TTL,
            json.dumps(result_data)
        )

        logger.info(f"Background job {job_id}: Processing complete")

    except Exception as e:
        logger.exception(f"Background job {job_id}: Unexpected error: {e}")
        try:
            redis = await get_redis()
            await redis.setex(
                f"voice_job:{job_id}",
                VOICE_JOB_TTL,
                json.dumps({
                    "status": JOB_STATUS_FAILED,
                    "error": str(e),
                    "error_message": "Sorry, something went wrong. Please try again.",
                })
            )
        except Exception:
            pass


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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle recording complete webhook.

    This endpoint is called when the caller finishes speaking.
    It starts async processing and returns immediately with a redirect
    to the status check endpoint.

    Async Pattern:
    1. Store job data in Redis
    2. Start background task for processing
    3. Return TwiML with "please wait" and redirect to status endpoint
    4. Status endpoint returns result when ready, or another redirect if still processing

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

        # Get session data from Redis (optional - only used for turn count)
        redis = await get_redis()
        session_key = f"voice_session:{session_id}"
        session_raw = await redis.get(session_key)

        if not session_raw:
            # Session not found - log warning but continue processing
            # Session is only used for turn counting, not required for processing
            logger.warning(f"Session not found (continuing anyway): {session_id}")

        # Find VOICE_OUTPUT node config
        nodes = deployment.agent.config.get("nodes", [])
        voice_output_config = {}
        for node in nodes:
            node_data = node.get("data", {})
            if node.get("type") == "VOICE_OUTPUT" or node_data.get("type") == "VOICE_OUTPUT":
                voice_output_config = node_data.get("config", {})
                break

        # Create job ID for async processing
        job_id = str(uuid.uuid4())

        # Store initial job status
        job_data = {
            "status": JOB_STATUS_PROCESSING,
            "deployment_id": deployment_id,
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
        }
        await redis.setex(
            f"voice_job:{job_id}",
            VOICE_JOB_TTL,
            json.dumps(job_data)
        )

        # Start background processing task
        # Note: We use asyncio.create_task instead of BackgroundTasks
        # because BackgroundTasks runs after the response, but we need
        # the task to start immediately
        task = asyncio.create_task(
            process_voice_workflow_background(
                job_id=job_id,
                deployment_id=deployment_id,
                agent_config=deployment.agent.config,
                recording_url=recording_data["recording_url"],
                session_id=session_id,
                organization_id=str(deployment.organization_id),
                agent_id=str(deployment.agent_id),
                provider_name=provider_name,
                credentials=credential.decrypted_value,
                voice_output_config=voice_output_config,
            )
        )

        # Add callback to log any unhandled exceptions from the background task
        def handle_task_exception(t):
            if t.cancelled():
                logger.warning(f"Background task {job_id} was cancelled")
            elif t.exception():
                logger.exception(f"Background task {job_id} failed with exception: {t.exception()}")

        task.add_done_callback(handle_task_exception)

        logger.info(
            f"Recording received, started async processing: "
            f"deployment={deployment_id}, session={session_id}, job={job_id}"
        )

        # Return immediately with redirect to status check endpoint
        base_url = get_original_base_url(request)
        status_url = (
            f"{base_url}api/v1/voice/webhook/status/{job_id}"
            f"?api_key={api_key}&amp;session_id={session_id}&amp;deployment_id={deployment_id}&amp;check=1"
        )

        # Generate TwiML with silent pause and redirect to status check
        # Note: URL is already XML-escaped with &amp; for & characters
        # Using silent pause instead of verbal message for better UX
        twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Pause length="3"/>
    <Redirect>{status_url}</Redirect>
</Response>'''

        return Response(
            content=twiml,
            media_type="application/xml",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error handling recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process recording",
        )


@router.post("/webhook/status/{job_id}")
@router.get("/webhook/status/{job_id}")
async def check_voice_job_status(
    job_id: str,
    request: Request,
    api_key: str,
    session_id: str,
    deployment_id: str,
    check: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """
    Check the status of an async voice processing job.

    This endpoint is called via Twilio <Redirect> to check if processing is complete.

    Flow:
    - If job is complete: Return audio response TwiML
    - If job is still processing: Return another redirect (with pause)
    - If job failed: Return error message TwiML
    - If max checks exceeded: Return timeout message TwiML
    """
    try:
        redis = await get_redis()

        # Check job status
        job_key = f"voice_job:{job_id}"
        job_raw = await redis.get(job_key)

        if not job_raw:
            logger.warning(f"Job not found: {job_id}")
            twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Sorry, your session has expired. Please try again.</Say>
    <Hangup/>
</Response>'''
            return Response(content=twiml, media_type="application/xml")

        job_data = json.loads(job_raw)
        job_status = job_data.get("status", JOB_STATUS_PROCESSING)

        logger.info(f"Status check for job {job_id}: status={job_status}, check={check}")

        # Job is still processing
        if job_status == JOB_STATUS_PROCESSING:
            # Check if we've exceeded max retries
            if check >= MAX_STATUS_CHECKS:
                logger.warning(f"Job {job_id} exceeded max status checks ({MAX_STATUS_CHECKS})")
                twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Sorry, processing is taking too long. Please try again later.</Say>
    <Hangup/>
</Response>'''
                return Response(content=twiml, media_type="application/xml")

            # Return another redirect with silent pause
            # Using silent pauses instead of verbal messages for better UX
            base_url = get_original_base_url(request)
            status_url = (
                f"{base_url}api/v1/voice/webhook/status/{job_id}"
                f"?api_key={api_key}&amp;session_id={session_id}&amp;deployment_id={deployment_id}&amp;check={check + 1}"
            )

            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Pause length="2"/>
    <Redirect>{status_url}</Redirect>
</Response>'''
            return Response(content=twiml, media_type="application/xml")

        # Job failed
        if job_status == JOB_STATUS_FAILED:
            error_message = job_data.get("error_message", "Sorry, an error occurred.")
            logger.warning(f"Job {job_id} failed: {job_data.get('error')}")
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">{error_message}</Say>
    <Hangup/>
</Response>'''
            return Response(content=twiml, media_type="application/xml")

        # Job completed successfully
        if job_status == JOB_STATUS_COMPLETE:
            logger.info(f"Job {job_id} completed successfully")

            # Get deployment for voice config
            deployment, credential, provider_name, voice_config = await get_deployment_and_credential(
                deployment_id, api_key, db
            )

            # Initialize provider for TwiML generation
            provider = get_voice_provider(provider_name, credential.decrypted_value)

            # Get voice output config
            voice_output_config = job_data.get("voice_output_config", {})
            after_action = voice_output_config.get("afterResponse", "continue")

            base_url = get_original_base_url(request)

            # Check if we have audio response
            audio_id = job_data.get("audio_id")
            if audio_id:
                audio_url = f"{base_url}api/v1/voice/audio/{audio_id}"

                if after_action == "continue":
                    # Build recording callback URL for continue action
                    recording_callback_url = (
                        f"{base_url}api/v1/voice/webhook/recording/{deployment_id}"
                        f"?api_key={api_key}&session_id={session_id}"
                    )
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
                # Text response fallback
                text_response = job_data.get(
                    "text_response",
                    voice_output_config.get("fallbackMessage", "I'm sorry, I don't have a response for that.")
                )

                if after_action == "continue":
                    recording_callback_url = (
                        f"{base_url}api/v1/voice/webhook/recording/{deployment_id}"
                        f"?api_key={api_key}&session_id={session_id}"
                    )
                    response = provider.generate_continue_response(
                        recording_callback_url=recording_callback_url,
                        prompt=text_response,
                        max_duration=voice_config.get("config", {}).get("maxDuration", 60),
                    )
                else:
                    response = provider.generate_text_response(
                        text=text_response,
                        after_action=after_action,
                    )

            # Update session turn count
            session_key = f"voice_session:{session_id}"
            session_raw = await redis.get(session_key)
            if session_raw:
                session_data = eval(session_raw)
                session_data["turn_count"] = session_data.get("turn_count", 0) + 1
                await redis.setex(session_key, VOICE_SESSION_TTL, str(session_data))

            # Clean up job data
            await redis.delete(job_key)

            return Response(
                content=response.content,
                media_type=response.content_type,
            )

        # Unknown status
        logger.error(f"Job {job_id} has unknown status: {job_status}")
        twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Sorry, an unexpected error occurred.</Say>
    <Hangup/>
</Response>'''
        return Response(content=twiml, media_type="application/xml")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error checking job status: {e}")
        twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">Sorry, an error occurred. Please try again.</Say>
    <Hangup/>
</Response>'''
        return Response(content=twiml, media_type="application/xml")


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
