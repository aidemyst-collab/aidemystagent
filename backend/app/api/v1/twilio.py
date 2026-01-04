"""
Twilio Integration Endpoints
Handles voice calls, recordings, media streams, and text-to-speech
"""
from fastapi import APIRouter, Request, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import base64
import logging

from app.core.database import get_db
from app.services.audio_transcription_service import AudioTranscriptionService
from app.services.text_to_speech_service import TextToSpeechService
from app.models.credential import Credential
from app.models.user import User
from app.api.deps import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class TranscribeRequest(BaseModel):
    """Request to transcribe audio."""
    audio_url: Optional[str] = None
    audio_data: Optional[str] = None  # Base64 encoded
    audio_format: str = "wav"
    provider: str = "openai_whisper"
    credential_id: str
    model: Optional[str] = None
    language: Optional[str] = None
    sample_rate: int = 8000
    twilio_format: bool = False


class TranscribeResponse(BaseModel):
    """Transcription response."""
    success: bool
    text: str
    confidence: Optional[float] = None
    provider: str
    model: Optional[str] = None
    error: Optional[str] = None


class SynthesizeRequest(BaseModel):
    """Request to synthesize speech from text."""
    text: str
    provider: str = "openai_tts"
    credential_id: str
    voice: Optional[str] = None
    model: Optional[str] = None
    output_format: str = "mp3"
    speed: float = 1.0
    language: Optional[str] = None


class SynthesizeResponse(BaseModel):
    """Text-to-speech response."""
    success: bool
    audio_data: str  # Base64 encoded audio
    audio_format: str
    provider: str
    voice: Optional[str] = None
    model: Optional[str] = None
    text_length: int = 0
    error: Optional[str] = None


class TwiMLRequest(BaseModel):
    """Request to generate TwiML response."""
    text: str
    voice: str = "alice"
    language: str = "en-US"
    action: str = "say"  # 'say' or 'play'
    audio_url: Optional[str] = None


class VoiceInfo(BaseModel):
    """Voice information."""
    id: str
    name: str
    gender: Optional[str] = None
    language: Optional[str] = None


# =============================================================================
# Transcription Endpoints
# =============================================================================

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    request: TranscribeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Transcribe audio to text.

    Supports:
    - Audio URL (e.g., Twilio recording URL)
    - Base64 encoded audio data
    - Multiple providers (OpenAI Whisper, Deepgram, etc.)
    """
    try:
        # Get credential
        credential = await db.get(Credential, request.credential_id)
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")

        # Get audio data
        if request.audio_url:
            # Transcribe from URL
            result = await AudioTranscriptionService.transcribe_from_url(
                url=request.audio_url,
                provider=request.provider,
                api_key=credential.api_key,
                model=request.model,
                language=request.language
            )
        elif request.audio_data:
            # Decode base64 audio
            audio_bytes = base64.b64decode(request.audio_data)

            # Handle Twilio mulaw format
            if request.twilio_format:
                audio_format = "mulaw"
            else:
                audio_format = request.audio_format

            # Create service and transcribe
            service = AudioTranscriptionService(
                provider=request.provider,
                api_key=credential.api_key,
                model=request.model
            )
            result = await service.transcribe(
                audio_data=audio_bytes,
                audio_format=audio_format,
                language=request.language,
                sample_rate=request.sample_rate
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either audio_url or audio_data must be provided"
            )

        return TranscribeResponse(
            success=result.get("success", True),
            text=result.get("text", ""),
            confidence=result.get("confidence"),
            provider=result.get("provider", request.provider),
            model=result.get("model"),
            error=result.get("error")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Text-to-Speech Endpoints
# =============================================================================

@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_speech(
    request: SynthesizeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Synthesize speech from text.

    Supports multiple providers:
    - OpenAI TTS (tts-1, tts-1-hd)
    - ElevenLabs
    - Google Cloud TTS
    - Amazon Polly
    """
    try:
        # Get credential
        credential = await db.get(Credential, request.credential_id)
        if not credential:
            raise HTTPException(status_code=404, detail="Credential not found")

        # Create TTS service
        service = TextToSpeechService(
            provider=request.provider,
            api_key=credential.api_key,
            voice=request.voice,
            model=request.model
        )

        # Synthesize speech
        result = await service.synthesize(
            text=request.text,
            output_format=request.output_format,
            speed=request.speed,
            language=request.language
        )

        return SynthesizeResponse(
            success=result.get("success", False),
            audio_data=result.get("audio_data", ""),
            audio_format=result.get("audio_format", request.output_format),
            provider=result.get("provider", request.provider),
            voice=result.get("voice"),
            model=result.get("model"),
            text_length=result.get("text_length", 0),
            error=result.get("error")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Speech synthesis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices/{provider}", response_model=List[VoiceInfo])
async def get_voices(
    provider: str,
    current_user: User = Depends(get_current_active_user),
):
    """
    Get available voices for a TTS provider.

    Supported providers:
    - openai_tts
    - elevenlabs
    - google_tts
    - amazon_polly
    """
    voices = TextToSpeechService.get_voices(provider)
    if not voices:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown provider: {provider}. Supported: openai_tts, elevenlabs, google_tts, amazon_polly"
        )

    return [VoiceInfo(**v) for v in voices]


@router.post("/twiml/say")
async def generate_twiml_say(request: TwiMLRequest):
    """
    Generate TwiML for Twilio to speak text.
    Uses Twilio's built-in TTS voices.
    """
    twiml = TextToSpeechService.generate_twilio_twiml(
        text=request.text,
        voice=request.voice,
        language=request.language
    )
    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/twiml/play")
async def generate_twiml_play(audio_url: str):
    """
    Generate TwiML for Twilio to play an audio file.
    Use this with pre-generated audio from /synthesize endpoint.
    """
    twiml = TextToSpeechService.generate_twilio_play_twiml(audio_url)
    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.get("/providers")
async def list_tts_providers():
    """
    List available TTS providers and their capabilities.
    """
    return {
        "providers": [
            {
                "id": "openai_tts",
                "name": "OpenAI TTS",
                "models": ["tts-1", "tts-1-hd"],
                "formats": ["mp3", "wav", "ogg", "flac", "aac"],
                "features": ["speed_control"],
            },
            {
                "id": "elevenlabs",
                "name": "ElevenLabs",
                "models": ["eleven_monolingual_v1", "eleven_multilingual_v2"],
                "formats": ["mp3", "wav", "mulaw"],
                "features": ["voice_cloning", "emotion_control"],
            },
            {
                "id": "google_tts",
                "name": "Google Cloud TTS",
                "models": ["Wavenet", "Neural2", "Standard"],
                "formats": ["mp3", "wav", "ogg", "mulaw"],
                "features": ["ssml", "multilingual"],
            },
            {
                "id": "amazon_polly",
                "name": "Amazon Polly",
                "models": ["neural", "standard"],
                "formats": ["mp3", "wav", "ogg", "pcm"],
                "features": ["ssml", "newscaster_style"],
            },
        ]
    }


# =============================================================================
# Twilio Voice Webhook Endpoints
# =============================================================================

@router.post("/voice/incoming")
async def handle_incoming_call(request: Request):
    """
    Handle incoming Twilio voice call.
    Returns TwiML to prompt user and record message.
    """
    twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Hello! Please speak your message after the beep. Press any key when finished.</Say>
    <Record
        maxLength="120"
        action="/api/v1/twilio/voice/recording"
        recordingStatusCallback="/api/v1/twilio/voice/recording-status"
        recordingStatusCallbackMethod="POST"
        playBeep="true"
        trim="trim-silence"
    />
    <Say voice="alice">I did not receive a recording. Goodbye.</Say>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/voice/recording")
async def handle_recording_complete(request: Request):
    """
    Handle completed recording from Twilio.
    This is called when the recording is complete.
    """
    try:
        form_data = await request.form()
        recording_url = form_data.get("RecordingUrl")
        recording_sid = form_data.get("RecordingSid")
        call_sid = form_data.get("CallSid")
        duration = form_data.get("RecordingDuration")

        logger.info(f"Recording received - SID: {recording_sid}, Duration: {duration}s")

        # Store recording info or trigger workflow
        # This can be extended to automatically process the recording

        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Thank you. Your message has been recorded and is being processed.</Say>
    <Hangup/>
</Response>"""
        return PlainTextResponse(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error handling recording: {str(e)}")
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Sorry, there was an error processing your message.</Say>
    <Hangup/>
</Response>"""
        return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/voice/recording-status")
async def handle_recording_status(request: Request):
    """
    Handle recording status callback from Twilio.
    Called when recording is ready for download.
    """
    try:
        form_data = await request.form()
        recording_status = form_data.get("RecordingStatus")
        recording_url = form_data.get("RecordingUrl")
        recording_sid = form_data.get("RecordingSid")

        logger.info(f"Recording status: {recording_status} - SID: {recording_sid}")

        if recording_status == "completed":
            # Recording is ready - can be processed
            # Add .mp3 or .wav to get the audio file
            audio_url = f"{recording_url}.mp3"
            logger.info(f"Recording available at: {audio_url}")

        return PlainTextResponse(content="OK", status_code=200)

    except Exception as e:
        logger.error(f"Error handling recording status: {str(e)}")
        return PlainTextResponse(content="Error", status_code=500)


# =============================================================================
# Twilio Media Stream (Real-time)
# =============================================================================

@router.websocket("/media-stream")
async def twilio_media_stream(websocket: WebSocket):
    """
    Handle real-time Twilio Media Stream for live transcription.

    Twilio sends audio chunks via WebSocket which can be
    transcribed in real-time or buffered for batch processing.
    """
    await websocket.accept()

    audio_buffer = bytearray()
    stream_sid = None
    call_sid = None

    logger.info("Twilio media stream connected")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event_type = message.get("event")

            if event_type == "connected":
                logger.info("Twilio stream connected")

            elif event_type == "start":
                stream_sid = message.get("streamSid")
                call_sid = message.get("start", {}).get("callSid")
                logger.info(f"Stream started - SID: {stream_sid}, Call: {call_sid}")

            elif event_type == "media":
                # Collect audio chunks (base64 encoded mulaw)
                payload = message.get("media", {}).get("payload", "")
                if payload:
                    audio_chunk = base64.b64decode(payload)
                    audio_buffer.extend(audio_chunk)

            elif event_type == "stop":
                logger.info(f"Stream stopped - collected {len(audio_buffer)} bytes")
                # Process the complete audio buffer here if needed
                break

            elif event_type == "mark":
                # Handle marks (sync points)
                mark_name = message.get("mark", {}).get("name")
                logger.debug(f"Mark received: {mark_name}")

    except WebSocketDisconnect:
        logger.info("Twilio media stream disconnected")
    except Exception as e:
        logger.error(f"Media stream error: {str(e)}")
    finally:
        await websocket.close()

    # Return collected audio (can be used for transcription)
    return bytes(audio_buffer)


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/twiml/gather")
async def get_gather_twiml(
    prompt: str = "Please speak now",
    language: str = "en-US",
    timeout: int = 5,
):
    """
    Generate TwiML for speech gathering.
    Useful for IVR and voice bots.
    """
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather input="speech" language="{language}" timeout="{timeout}" action="/api/v1/twilio/voice/process-speech">
        <Say voice="alice">{prompt}</Say>
    </Gather>
    <Say voice="alice">I didn't hear anything. Goodbye.</Say>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")


@router.post("/voice/process-speech")
async def process_speech_input(request: Request):
    """
    Process speech input from Twilio Gather.
    Twilio provides SpeechResult with the transcribed text.
    """
    try:
        form_data = await request.form()
        speech_result = form_data.get("SpeechResult", "")
        confidence = form_data.get("Confidence", "0")

        logger.info(f"Speech received: '{speech_result}' (confidence: {confidence})")

        # Process the speech result
        # This can trigger a workflow or return a response

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">You said: {speech_result}. Thank you!</Say>
    <Hangup/>
</Response>"""
        return PlainTextResponse(content=twiml, media_type="application/xml")

    except Exception as e:
        logger.error(f"Error processing speech: {str(e)}")
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Sorry, I couldn't process your speech.</Say>
    <Hangup/>
</Response>"""
        return PlainTextResponse(content=twiml, media_type="application/xml")
