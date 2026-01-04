"""
Audio Transcription Service - Supports multiple providers
Optimized for Twilio audio format (mulaw, 8kHz)
"""
import httpx
import base64
import struct
import wave
import io
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TranscriptionProvider(str, Enum):
    OPENAI_WHISPER = "openai_whisper"
    DEEPGRAM = "deepgram"
    GOOGLE_STT = "google_stt"
    ASSEMBLYAI = "assemblyai"


class AudioTranscriptionService:
    """Service for transcribing audio to text."""

    def __init__(
        self,
        provider: str,
        api_key: str,
        model: Optional[str] = None
    ):
        """
        Initialize Audio Transcription service.

        Args:
            provider: Transcription provider (openai_whisper, deepgram, etc.)
            api_key: API key for the provider
            model: Optional model name
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model

    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: str = "wav",
        language: Optional[str] = None,
        sample_rate: int = 8000
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text.

        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format (wav, mp3, mulaw, ogg, webm)
            language: Optional language code (e.g., 'en', 'es')
            sample_rate: Audio sample rate in Hz

        Returns:
            Dict with transcription result
        """
        if self.provider == TranscriptionProvider.OPENAI_WHISPER.value:
            return await self._transcribe_openai(audio_data, audio_format, language)
        elif self.provider == TranscriptionProvider.DEEPGRAM.value:
            return await self._transcribe_deepgram(audio_data, audio_format, language, sample_rate)
        elif self.provider == TranscriptionProvider.ASSEMBLYAI.value:
            return await self._transcribe_assemblyai(audio_data, audio_format, language)
        elif self.provider == TranscriptionProvider.GOOGLE_STT.value:
            return await self._transcribe_google(audio_data, audio_format, language, sample_rate)
        else:
            raise ValueError(f"Unsupported transcription provider: {self.provider}")

    async def _transcribe_openai(
        self,
        audio_data: bytes,
        audio_format: str,
        language: Optional[str]
    ) -> Dict[str, Any]:
        """Transcribe using OpenAI Whisper API."""
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.api_key)

            # Convert mulaw to wav if needed (Whisper requires specific formats)
            if audio_format == "mulaw":
                audio_data = self._mulaw_to_wav(audio_data)
                audio_format = "wav"

            # Create a file-like object
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{audio_format}"

            kwargs = {
                "model": self.model or "whisper-1",
                "file": audio_file,
            }
            if language:
                kwargs["language"] = language

            response = await client.audio.transcriptions.create(**kwargs)

            return {
                "text": response.text,
                "provider": "openai_whisper",
                "model": self.model or "whisper-1",
                "success": True
            }
        except Exception as e:
            logger.error(f"OpenAI Whisper transcription failed: {str(e)}")
            return {
                "text": "",
                "error": str(e),
                "provider": "openai_whisper",
                "success": False
            }

    async def _transcribe_deepgram(
        self,
        audio_data: bytes,
        audio_format: str,
        language: Optional[str],
        sample_rate: int
    ) -> Dict[str, Any]:
        """Transcribe using Deepgram API."""
        try:
            # Map audio format to content type
            content_type_map = {
                "wav": "audio/wav",
                "mp3": "audio/mpeg",
                "mulaw": "audio/mulaw",
                "ogg": "audio/ogg",
                "webm": "audio/webm",
                "flac": "audio/flac",
            }
            content_type = content_type_map.get(audio_format, "audio/wav")

            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type": content_type
                }

                params = {
                    "model": self.model or "nova-2",
                    "smart_format": "true",
                    "punctuate": "true",
                }

                if audio_format == "mulaw":
                    params["encoding"] = "mulaw"
                    params["sample_rate"] = sample_rate
                    params["channels"] = 1

                if language:
                    params["language"] = language

                response = await client.post(
                    "https://api.deepgram.com/v1/listen",
                    headers=headers,
                    params=params,
                    content=audio_data
                )
                response.raise_for_status()
                data = response.json()

                # Extract transcript from Deepgram response
                channels = data.get("results", {}).get("channels", [])
                if channels:
                    alternatives = channels[0].get("alternatives", [])
                    if alternatives:
                        return {
                            "text": alternatives[0].get("transcript", ""),
                            "confidence": alternatives[0].get("confidence", 0),
                            "words": alternatives[0].get("words", []),
                            "provider": "deepgram",
                            "model": self.model or "nova-2",
                            "success": True
                        }

                return {
                    "text": "",
                    "provider": "deepgram",
                    "success": True
                }

        except Exception as e:
            logger.error(f"Deepgram transcription failed: {str(e)}")
            return {
                "text": "",
                "error": str(e),
                "provider": "deepgram",
                "success": False
            }

    async def _transcribe_assemblyai(
        self,
        audio_data: bytes,
        audio_format: str,
        language: Optional[str]
    ) -> Dict[str, Any]:
        """Transcribe using AssemblyAI API."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                headers = {
                    "Authorization": self.api_key,
                    "Content-Type": "application/octet-stream"
                }

                # Step 1: Upload audio
                upload_response = await client.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers=headers,
                    content=audio_data
                )
                upload_response.raise_for_status()
                upload_url = upload_response.json()["upload_url"]

                # Step 2: Request transcription
                transcript_request = {
                    "audio_url": upload_url,
                }
                if language:
                    transcript_request["language_code"] = language

                headers["Content-Type"] = "application/json"
                transcript_response = await client.post(
                    "https://api.assemblyai.com/v2/transcript",
                    headers=headers,
                    json=transcript_request
                )
                transcript_response.raise_for_status()
                transcript_id = transcript_response.json()["id"]

                # Step 3: Poll for completion
                import asyncio
                while True:
                    poll_response = await client.get(
                        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                        headers={"Authorization": self.api_key}
                    )
                    poll_data = poll_response.json()

                    if poll_data["status"] == "completed":
                        return {
                            "text": poll_data.get("text", ""),
                            "confidence": poll_data.get("confidence", 0),
                            "words": poll_data.get("words", []),
                            "provider": "assemblyai",
                            "success": True
                        }
                    elif poll_data["status"] == "error":
                        return {
                            "text": "",
                            "error": poll_data.get("error", "Transcription failed"),
                            "provider": "assemblyai",
                            "success": False
                        }

                    await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"AssemblyAI transcription failed: {str(e)}")
            return {
                "text": "",
                "error": str(e),
                "provider": "assemblyai",
                "success": False
            }

    async def _transcribe_google(
        self,
        audio_data: bytes,
        audio_format: str,
        language: Optional[str],
        sample_rate: int
    ) -> Dict[str, Any]:
        """Transcribe using Google Cloud Speech-to-Text API."""
        try:
            from google.cloud import speech_v1 as speech
            from google.oauth2 import service_account
            import json

            # Parse service account JSON from API key
            credentials_info = json.loads(self.api_key)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)

            client = speech.SpeechClient(credentials=credentials)

            # Map audio format to encoding
            encoding_map = {
                "wav": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                "mulaw": speech.RecognitionConfig.AudioEncoding.MULAW,
                "mp3": speech.RecognitionConfig.AudioEncoding.MP3,
                "flac": speech.RecognitionConfig.AudioEncoding.FLAC,
                "ogg": speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            }

            config = speech.RecognitionConfig(
                encoding=encoding_map.get(audio_format, speech.RecognitionConfig.AudioEncoding.LINEAR16),
                sample_rate_hertz=sample_rate,
                language_code=language or "en-US",
            )

            audio = speech.RecognitionAudio(content=audio_data)

            response = client.recognize(config=config, audio=audio)

            # Extract transcript
            transcript = ""
            confidence = 0
            for result in response.results:
                transcript += result.alternatives[0].transcript
                confidence = result.alternatives[0].confidence

            return {
                "text": transcript,
                "confidence": confidence,
                "provider": "google_stt",
                "success": True
            }

        except Exception as e:
            logger.error(f"Google STT transcription failed: {str(e)}")
            return {
                "text": "",
                "error": str(e),
                "provider": "google_stt",
                "success": False
            }

    @staticmethod
    def decode_twilio_audio(payload: str) -> bytes:
        """
        Decode Twilio media stream payload (base64 encoded mulaw audio).

        Args:
            payload: Base64 encoded audio from Twilio

        Returns:
            Raw audio bytes
        """
        return base64.b64decode(payload)

    @staticmethod
    def _mulaw_to_wav(mulaw_data: bytes, sample_rate: int = 8000) -> bytes:
        """
        Convert mulaw audio to WAV format.

        Args:
            mulaw_data: Raw mulaw audio bytes
            sample_rate: Sample rate (default 8000 for Twilio)

        Returns:
            WAV formatted audio bytes
        """
        # Mulaw decoding table
        def mulaw_decode(mu_val):
            mu_val = ~mu_val
            sign = (mu_val & 0x80)
            exponent = (mu_val >> 4) & 0x07
            mantissa = mu_val & 0x0F
            sample = ((mantissa << 3) + 0x84) << exponent
            sample -= 0x84
            if sign:
                sample = -sample
            return sample

        # Decode mulaw to PCM
        pcm_data = []
        for byte in mulaw_data:
            pcm_data.append(mulaw_decode(byte))

        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(struct.pack(f'<{len(pcm_data)}h', *pcm_data))

        wav_buffer.seek(0)
        return wav_buffer.read()

    @staticmethod
    async def transcribe_from_url(
        url: str,
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio from a URL (e.g., Twilio recording URL).

        Args:
            url: URL to the audio file
            provider: Transcription provider
            api_key: API key
            model: Optional model name
            language: Optional language code

        Returns:
            Transcription result
        """
        # Download audio from URL
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            audio_data = response.content

        # Determine format from URL or content type
        content_type = response.headers.get("content-type", "")
        if "wav" in content_type or url.endswith(".wav"):
            audio_format = "wav"
        elif "mp3" in content_type or "mpeg" in content_type or url.endswith(".mp3"):
            audio_format = "mp3"
        else:
            audio_format = "wav"  # Default

        # Transcribe
        service = AudioTranscriptionService(provider, api_key, model)
        return await service.transcribe(audio_data, audio_format, language)
