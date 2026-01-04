"""
Text-to-Speech Service - Supports multiple providers
Optimized for Twilio voice responses and audio generation
"""
import httpx
import base64
import io
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TTSProvider(str, Enum):
    OPENAI_TTS = "openai_tts"
    ELEVENLABS = "elevenlabs"
    GOOGLE_TTS = "google_tts"
    AMAZON_POLLY = "amazon_polly"


class TextToSpeechService:
    """Service for converting text to speech audio."""

    # Voice options per provider
    VOICES = {
        "openai_tts": [
            {"id": "alloy", "name": "Alloy", "gender": "neutral"},
            {"id": "echo", "name": "Echo", "gender": "male"},
            {"id": "fable", "name": "Fable", "gender": "neutral"},
            {"id": "onyx", "name": "Onyx", "gender": "male"},
            {"id": "nova", "name": "Nova", "gender": "female"},
            {"id": "shimmer", "name": "Shimmer", "gender": "female"},
        ],
        "elevenlabs": [
            {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel", "gender": "female"},
            {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "gender": "female"},
            {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella", "gender": "female"},
            {"id": "ErXwobaYiN019PkySvjV", "name": "Antoni", "gender": "male"},
            {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "gender": "female"},
            {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "gender": "male"},
            {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold", "gender": "male"},
            {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam", "gender": "male"},
            {"id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam", "gender": "male"},
        ],
        "google_tts": [
            {"id": "en-US-Wavenet-A", "name": "Wavenet A", "gender": "male", "language": "en-US"},
            {"id": "en-US-Wavenet-B", "name": "Wavenet B", "gender": "male", "language": "en-US"},
            {"id": "en-US-Wavenet-C", "name": "Wavenet C", "gender": "female", "language": "en-US"},
            {"id": "en-US-Wavenet-D", "name": "Wavenet D", "gender": "male", "language": "en-US"},
            {"id": "en-US-Wavenet-E", "name": "Wavenet E", "gender": "female", "language": "en-US"},
            {"id": "en-US-Wavenet-F", "name": "Wavenet F", "gender": "female", "language": "en-US"},
            {"id": "en-US-Neural2-A", "name": "Neural2 A", "gender": "male", "language": "en-US"},
            {"id": "en-US-Neural2-C", "name": "Neural2 C", "gender": "female", "language": "en-US"},
        ],
        "amazon_polly": [
            {"id": "Joanna", "name": "Joanna", "gender": "female", "engine": "neural"},
            {"id": "Matthew", "name": "Matthew", "gender": "male", "engine": "neural"},
            {"id": "Ivy", "name": "Ivy", "gender": "female", "engine": "neural"},
            {"id": "Kendra", "name": "Kendra", "gender": "female", "engine": "neural"},
            {"id": "Kimberly", "name": "Kimberly", "gender": "female", "engine": "neural"},
            {"id": "Salli", "name": "Salli", "gender": "female", "engine": "neural"},
            {"id": "Joey", "name": "Joey", "gender": "male", "engine": "neural"},
            {"id": "Justin", "name": "Justin", "gender": "male", "engine": "neural"},
        ],
    }

    def __init__(
        self,
        provider: str,
        api_key: str,
        voice: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize Text-to-Speech service.

        Args:
            provider: TTS provider (openai_tts, elevenlabs, google_tts, amazon_polly)
            api_key: API key for the provider
            voice: Voice ID to use
            model: Optional model name
        """
        self.provider = provider
        self.api_key = api_key
        self.voice = voice
        self.model = model

    async def synthesize(
        self,
        text: str,
        output_format: str = "mp3",
        speed: float = 1.0,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize speech from text.

        Args:
            text: Text to convert to speech
            output_format: Audio format (mp3, wav, ogg, pcm, mulaw)
            speed: Speech speed (0.5 to 2.0)
            language: Language code for multilingual voices

        Returns:
            Dict with audio data (base64), format, duration, etc.
        """
        if self.provider == TTSProvider.OPENAI_TTS.value:
            return await self._synthesize_openai(text, output_format, speed)
        elif self.provider == TTSProvider.ELEVENLABS.value:
            return await self._synthesize_elevenlabs(text, output_format, speed)
        elif self.provider == TTSProvider.GOOGLE_TTS.value:
            return await self._synthesize_google(text, output_format, speed, language)
        elif self.provider == TTSProvider.AMAZON_POLLY.value:
            return await self._synthesize_polly(text, output_format, speed, language)
        else:
            raise ValueError(f"Unsupported TTS provider: {self.provider}")

    async def _synthesize_openai(
        self,
        text: str,
        output_format: str,
        speed: float
    ) -> Dict[str, Any]:
        """Synthesize using OpenAI TTS API."""
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.api_key)

            # Map format to OpenAI response format
            format_map = {
                "mp3": "mp3",
                "wav": "wav",
                "ogg": "opus",
                "flac": "flac",
                "aac": "aac",
            }
            response_format = format_map.get(output_format, "mp3")

            # Default voice if not specified
            voice = self.voice or "alloy"

            response = await client.audio.speech.create(
                model=self.model or "tts-1",
                voice=voice,
                input=text,
                response_format=response_format,
                speed=speed
            )

            # Get audio bytes
            audio_bytes = response.content

            return {
                "audio_data": base64.b64encode(audio_bytes).decode("utf-8"),
                "audio_format": output_format,
                "provider": "openai_tts",
                "voice": voice,
                "model": self.model or "tts-1",
                "text_length": len(text),
                "success": True
            }

        except Exception as e:
            logger.error(f"OpenAI TTS failed: {str(e)}")
            return {
                "audio_data": "",
                "error": str(e),
                "provider": "openai_tts",
                "success": False
            }

    async def _synthesize_elevenlabs(
        self,
        text: str,
        output_format: str,
        speed: float
    ) -> Dict[str, Any]:
        """Synthesize using ElevenLabs API."""
        try:
            # Default voice if not specified
            voice_id = self.voice or "21m00Tcm4TlvDq8ikWAM"  # Rachel

            # Map format to ElevenLabs output format
            format_map = {
                "mp3": "mp3_44100_128",
                "wav": "pcm_44100",
                "ogg": "mp3_44100_128",  # Fallback to mp3
                "mulaw": "ulaw_8000",  # For Twilio
            }
            eleven_format = format_map.get(output_format, "mp3_44100_128")

            async with httpx.AsyncClient(timeout=60.0) as client:
                headers = {
                    "xi-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg"
                }

                payload = {
                    "text": text,
                    "model_id": self.model or "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.0,
                        "use_speaker_boost": True
                    }
                }

                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers=headers,
                    json=payload,
                    params={"output_format": eleven_format}
                )
                response.raise_for_status()

                audio_bytes = response.content

                return {
                    "audio_data": base64.b64encode(audio_bytes).decode("utf-8"),
                    "audio_format": output_format,
                    "provider": "elevenlabs",
                    "voice": voice_id,
                    "model": self.model or "eleven_monolingual_v1",
                    "text_length": len(text),
                    "success": True
                }

        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {str(e)}")
            return {
                "audio_data": "",
                "error": str(e),
                "provider": "elevenlabs",
                "success": False
            }

    async def _synthesize_google(
        self,
        text: str,
        output_format: str,
        speed: float,
        language: Optional[str]
    ) -> Dict[str, Any]:
        """Synthesize using Google Cloud Text-to-Speech API."""
        try:
            from google.cloud import texttospeech_v1 as texttospeech
            from google.oauth2 import service_account
            import json

            # Parse service account JSON from API key
            credentials_info = json.loads(self.api_key)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)

            client = texttospeech.TextToSpeechClient(credentials=credentials)

            # Map format to Google audio encoding
            encoding_map = {
                "mp3": texttospeech.AudioEncoding.MP3,
                "wav": texttospeech.AudioEncoding.LINEAR16,
                "ogg": texttospeech.AudioEncoding.OGG_OPUS,
                "mulaw": texttospeech.AudioEncoding.MULAW,
            }
            audio_encoding = encoding_map.get(output_format, texttospeech.AudioEncoding.MP3)

            # Default voice
            voice_name = self.voice or "en-US-Wavenet-C"
            lang_code = language or "en-US"

            synthesis_input = texttospeech.SynthesisInput(text=text)

            voice = texttospeech.VoiceSelectionParams(
                language_code=lang_code,
                name=voice_name
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=audio_encoding,
                speaking_rate=speed
            )

            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            return {
                "audio_data": base64.b64encode(response.audio_content).decode("utf-8"),
                "audio_format": output_format,
                "provider": "google_tts",
                "voice": voice_name,
                "language": lang_code,
                "text_length": len(text),
                "success": True
            }

        except Exception as e:
            logger.error(f"Google TTS failed: {str(e)}")
            return {
                "audio_data": "",
                "error": str(e),
                "provider": "google_tts",
                "success": False
            }

    async def _synthesize_polly(
        self,
        text: str,
        output_format: str,
        speed: float,
        language: Optional[str]
    ) -> Dict[str, Any]:
        """Synthesize using Amazon Polly."""
        try:
            import boto3
            import json

            # Parse AWS credentials from API key (expected JSON format)
            creds = json.loads(self.api_key)

            polly_client = boto3.client(
                'polly',
                aws_access_key_id=creds.get('aws_access_key_id'),
                aws_secret_access_key=creds.get('aws_secret_access_key'),
                region_name=creds.get('region', 'us-east-1')
            )

            # Map format to Polly output format
            format_map = {
                "mp3": "mp3",
                "wav": "pcm",
                "ogg": "ogg_vorbis",
                "mulaw": "pcm",  # Will need conversion
            }
            polly_format = format_map.get(output_format, "mp3")

            # Default voice
            voice_id = self.voice or "Joanna"

            # Apply SSML for speed control if not 1.0
            if speed != 1.0:
                rate_percent = int(speed * 100)
                ssml_text = f'<speak><prosody rate="{rate_percent}%">{text}</prosody></speak>'
                text_type = 'ssml'
            else:
                ssml_text = text
                text_type = 'text'

            response = polly_client.synthesize_speech(
                Text=ssml_text,
                TextType=text_type,
                OutputFormat=polly_format,
                VoiceId=voice_id,
                Engine='neural'
            )

            # Read audio stream
            audio_bytes = response['AudioStream'].read()

            return {
                "audio_data": base64.b64encode(audio_bytes).decode("utf-8"),
                "audio_format": output_format,
                "provider": "amazon_polly",
                "voice": voice_id,
                "text_length": len(text),
                "success": True
            }

        except Exception as e:
            logger.error(f"Amazon Polly TTS failed: {str(e)}")
            return {
                "audio_data": "",
                "error": str(e),
                "provider": "amazon_polly",
                "success": False
            }

    @staticmethod
    def get_voices(provider: str) -> List[Dict[str, str]]:
        """Get available voices for a provider."""
        return TextToSpeechService.VOICES.get(provider, [])

    @staticmethod
    def generate_twilio_twiml(
        text: str,
        voice: str = "alice",
        language: str = "en-US"
    ) -> str:
        """
        Generate TwiML for Twilio voice response.

        Args:
            text: Text to speak
            voice: Twilio voice name (alice, man, woman, or Polly voice)
            language: Language code

        Returns:
            TwiML XML string
        """
        # Escape XML special characters
        import html
        escaped_text = html.escape(text)

        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{voice}" language="{language}">{escaped_text}</Say>
</Response>"""
        return twiml

    @staticmethod
    def generate_twilio_play_twiml(audio_url: str) -> str:
        """
        Generate TwiML to play an audio file.

        Args:
            audio_url: URL to the audio file

        Returns:
            TwiML XML string
        """
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Play>{audio_url}</Play>
</Response>"""
        return twiml

    @staticmethod
    async def save_audio_file(
        audio_data: str,
        file_path: str,
        audio_format: str = "mp3"
    ) -> str:
        """
        Save base64 audio data to a file.

        Args:
            audio_data: Base64 encoded audio
            file_path: Path to save the file
            audio_format: Audio format extension

        Returns:
            Path to the saved file
        """
        import aiofiles

        audio_bytes = base64.b64decode(audio_data)

        if not file_path.endswith(f".{audio_format}"):
            file_path = f"{file_path}.{audio_format}"

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(audio_bytes)

        return file_path
