"""
Twilio Voice Provider Implementation

Handles voice calls via Twilio's API using TwiML responses.
"""

import hmac
import hashlib
import base64
from typing import Optional

import httpx

from .base import VoiceProvider, VoiceProviderError, VoiceResponse, RecordingData


class TwilioProvider(VoiceProvider):
    """
    Twilio voice provider implementation.

    Uses TwiML (XML) format for responses.
    """

    provider_name = "twilio"

    def _validate_credentials(self) -> None:
        """Validate Twilio credentials."""
        required_fields = ["account_sid", "auth_token"]
        for field in required_fields:
            if field not in self.credentials:
                raise VoiceProviderError(
                    f"Missing required Twilio credential: {field}"
                )

        self.account_sid = self.credentials["account_sid"]
        self.auth_token = self.credentials["auth_token"]
        self.phone_number = self.credentials.get("phone_number")

    def get_content_type(self) -> str:
        """Return TwiML content type."""
        return "application/xml"

    def _twiml(self, content: str) -> str:
        """Wrap content in TwiML Response tags."""
        return f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>{content}</Response>'

    def generate_greeting_response(
        self,
        greeting: str,
        recording_callback_url: str,
        language: str = "en-US",
        max_duration: int = 60,
        play_beep: bool = True,
        silence_timeout: int = 5,
    ) -> VoiceResponse:
        """Generate TwiML for greeting and recording."""
        # Map language codes to Twilio voice names
        voice = self._get_voice_for_language(language)

        beep_attr = 'playBeep="true"' if play_beep else 'playBeep="false"'

        twiml = self._twiml(
            f'<Say voice="{voice}" language="{language}">{self._escape_xml(greeting)}</Say>'
            f'<Record maxLength="{max_duration}" action="{self._escape_xml(recording_callback_url)}" '
            f'{beep_attr} timeout="{silence_timeout}" transcribe="false"/>'
        )

        return VoiceResponse(
            content=twiml,
            content_type=self.get_content_type(),
        )

    def generate_audio_response(
        self,
        audio_url: str,
        after_action: str = "hangup",
        transfer_to: Optional[str] = None,
        loop: int = 1,
        recording_callback_url: Optional[str] = None,
        max_duration: int = 60,
        silence_timeout: int = 5,
    ) -> VoiceResponse:
        """Generate TwiML to play audio."""
        content = f'<Play loop="{loop}">{self._escape_xml(audio_url)}</Play>'

        if after_action == "hangup":
            content += "<Hangup/>"
        elif after_action == "transfer" and transfer_to:
            content += f'<Dial>{self._escape_xml(transfer_to)}</Dial>'
        elif after_action == "continue" and recording_callback_url:
            # Add Record element to continue the conversation
            content += (
                f'<Record maxLength="{max_duration}" action="{self._escape_xml(recording_callback_url)}" '
                f'playBeep="true" timeout="{silence_timeout}" transcribe="false"/>'
            )

        return VoiceResponse(
            content=self._twiml(content),
            content_type=self.get_content_type(),
        )

    def generate_text_response(
        self,
        text: str,
        voice: str = "alice",
        language: str = "en-US",
        after_action: str = "hangup",
    ) -> VoiceResponse:
        """Generate TwiML to speak text."""
        content = f'<Say voice="{voice}" language="{language}">{self._escape_xml(text)}</Say>'

        if after_action == "hangup":
            content += "<Hangup/>"

        return VoiceResponse(
            content=self._twiml(content),
            content_type=self.get_content_type(),
        )

    def generate_hangup_response(
        self,
        goodbye_message: Optional[str] = None,
        language: str = "en-US",
    ) -> VoiceResponse:
        """Generate TwiML to hang up."""
        voice = self._get_voice_for_language(language)
        content = ""

        if goodbye_message:
            content += f'<Say voice="{voice}" language="{language}">{self._escape_xml(goodbye_message)}</Say>'

        content += "<Hangup/>"

        return VoiceResponse(
            content=self._twiml(content),
            content_type=self.get_content_type(),
        )

    def generate_continue_response(
        self,
        recording_callback_url: str,
        prompt: Optional[str] = None,
        language: str = "en-US",
        max_duration: int = 60,
        silence_timeout: int = 5,
    ) -> VoiceResponse:
        """Generate TwiML to continue conversation."""
        voice = self._get_voice_for_language(language)
        content = ""

        if prompt:
            content += f'<Say voice="{voice}" language="{language}">{self._escape_xml(prompt)}</Say>'

        content += (
            f'<Record maxLength="{max_duration}" action="{self._escape_xml(recording_callback_url)}" '
            f'playBeep="true" timeout="{silence_timeout}" transcribe="false"/>'
        )

        return VoiceResponse(
            content=self._twiml(content),
            content_type=self.get_content_type(),
        )

    async def fetch_recording(self, recording_url: str) -> RecordingData:
        """Fetch recording from Twilio."""
        # Ensure we're fetching the audio file
        if not recording_url.endswith(".mp3"):
            recording_url = f"{recording_url}.mp3"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    recording_url,
                    auth=(self.account_sid, self.auth_token),
                    follow_redirects=True,
                    timeout=30.0,
                )
                response.raise_for_status()

                return RecordingData(
                    audio_data=response.content,
                    audio_format="mp3",
                )
        except httpx.HTTPError as e:
            raise VoiceProviderError(f"Failed to fetch Twilio recording: {str(e)}")

    def parse_incoming_call(self, request_data: dict) -> dict:
        """Parse Twilio incoming call webhook."""
        return {
            "call_sid": request_data.get("CallSid", ""),
            "caller_id": request_data.get("From", ""),
            "called_number": request_data.get("To", ""),
            "direction": request_data.get("Direction", "inbound"),
            "caller_city": request_data.get("FromCity"),
            "caller_state": request_data.get("FromState"),
            "caller_country": request_data.get("FromCountry"),
        }

    def parse_recording_complete(self, request_data: dict) -> dict:
        """Parse Twilio recording complete webhook."""
        return {
            "call_sid": request_data.get("CallSid", ""),
            "recording_url": request_data.get("RecordingUrl", ""),
            "recording_sid": request_data.get("RecordingSid", ""),
            "recording_duration": int(request_data.get("RecordingDuration", 0)),
        }

    def validate_webhook_signature(
        self,
        request_url: str,
        request_body: dict,
        signature: str,
    ) -> bool:
        """
        Validate Twilio webhook signature.

        Twilio uses HMAC-SHA1 for signature validation.
        The signature is computed from:
        1. The full URL (including query string)
        2. POST parameters sorted alphabetically, concatenated as key=value pairs
        """
        # Build the signature base string
        # Twilio concatenates params directly (no URL encoding, no delimiters between pairs)
        sorted_params = sorted(request_body.items())
        param_string = request_url + "".join(f"{k}{v}" for k, v in sorted_params)

        # Compute the expected signature
        expected_signature = base64.b64encode(
            hmac.new(
                self.auth_token.encode("utf-8"),
                param_string.encode("utf-8"),
                hashlib.sha1,
            ).digest()
        ).decode("utf-8")

        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)

    def _escape_xml(self, text: str) -> str:
        """Escape special XML characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def _get_voice_for_language(self, language: str) -> str:
        """Get appropriate Twilio voice for language."""
        voice_mapping = {
            "en-US": "Polly.Joanna",
            "en-GB": "Polly.Amy",
            "ar-AE": "Polly.Zeina",
            "ar-SA": "Polly.Zeina",
            "hi-IN": "Polly.Aditi",
            "fr-FR": "Polly.Celine",
            "de-DE": "Polly.Vicki",
            "es-ES": "Polly.Lucia",
        }
        return voice_mapping.get(language, "Polly.Joanna")
