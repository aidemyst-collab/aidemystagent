"""
Etisalat CPaaS (e&) Voice Provider Implementation

Handles voice calls via Etisalat's engageX Nexus platform.
Uses JSON format for responses.
"""

import hmac
import hashlib
import json
from typing import Optional

import httpx

from .base import VoiceProvider, VoiceProviderError, VoiceResponse, RecordingData


class EtisalatProvider(VoiceProvider):
    """
    Etisalat CPaaS voice provider implementation.

    Uses JSON format for responses.
    Native support for UAE and MENA region.
    TRA compliant out of the box.
    """

    provider_name = "etisalat"

    # Etisalat API base URL (placeholder - actual URL from e& enterprise agreement)
    API_BASE_URL = "https://api.engagex.eand.com/v1"

    def _validate_credentials(self) -> None:
        """Validate Etisalat credentials."""
        required_fields = ["api_key", "account_id"]
        for field in required_fields:
            if field not in self.credentials:
                raise VoiceProviderError(
                    f"Missing required Etisalat credential: {field}"
                )

        self.api_key = self.credentials["api_key"]
        self.api_secret = self.credentials.get("api_secret", "")
        self.account_id = self.credentials["account_id"]
        self.sender_id = self.credentials.get("sender_id")
        self.webhook_secret = self.credentials.get("webhook_secret", "")

    def get_content_type(self) -> str:
        """Return JSON content type."""
        return "application/json"

    def _json_response(self, actions: list) -> str:
        """Format actions as JSON response."""
        return json.dumps({"actions": actions}, ensure_ascii=False)

    def generate_greeting_response(
        self,
        greeting: str,
        recording_callback_url: str,
        language: str = "en-US",
        max_duration: int = 60,
        play_beep: bool = True,
    ) -> VoiceResponse:
        """Generate JSON for greeting and recording."""
        actions = [
            {
                "action": "say",
                "text": greeting,
                "language": language,
                "voice": self._get_voice_for_language(language),
            },
            {
                "action": "record",
                "max_duration": max_duration,
                "beep": play_beep,
                "silence_timeout": 3,
                "callback_url": recording_callback_url,
            },
        ]

        return VoiceResponse(
            content=self._json_response(actions),
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
    ) -> VoiceResponse:
        """Generate JSON to play audio."""
        actions = [
            {
                "action": "play",
                "url": audio_url,
                "loop": loop,
            }
        ]

        if after_action == "hangup":
            actions.append({"action": "hangup"})
        elif after_action == "transfer" and transfer_to:
            actions.append({
                "action": "transfer",
                "destination": transfer_to,
            })
        elif after_action == "continue" and recording_callback_url:
            # Add record action to continue the conversation
            actions.append({
                "action": "record",
                "max_duration": max_duration,
                "beep": True,
                "silence_timeout": 3,
                "callback_url": recording_callback_url,
            })

        return VoiceResponse(
            content=self._json_response(actions),
            content_type=self.get_content_type(),
        )

    def generate_text_response(
        self,
        text: str,
        voice: str = "default",
        language: str = "en-US",
        after_action: str = "hangup",
    ) -> VoiceResponse:
        """Generate JSON to speak text."""
        actions = [
            {
                "action": "say",
                "text": text,
                "language": language,
                "voice": voice if voice != "default" else self._get_voice_for_language(language),
            }
        ]

        if after_action == "hangup":
            actions.append({"action": "hangup"})

        return VoiceResponse(
            content=self._json_response(actions),
            content_type=self.get_content_type(),
        )

    def generate_hangup_response(
        self,
        goodbye_message: Optional[str] = None,
        language: str = "en-US",
    ) -> VoiceResponse:
        """Generate JSON to hang up."""
        actions = []

        if goodbye_message:
            actions.append({
                "action": "say",
                "text": goodbye_message,
                "language": language,
                "voice": self._get_voice_for_language(language),
            })

        actions.append({"action": "hangup"})

        return VoiceResponse(
            content=self._json_response(actions),
            content_type=self.get_content_type(),
        )

    def generate_continue_response(
        self,
        recording_callback_url: str,
        prompt: Optional[str] = None,
        language: str = "en-US",
        max_duration: int = 60,
    ) -> VoiceResponse:
        """Generate JSON to continue conversation."""
        actions = []

        if prompt:
            actions.append({
                "action": "say",
                "text": prompt,
                "language": language,
                "voice": self._get_voice_for_language(language),
            })

        actions.append({
            "action": "record",
            "max_duration": max_duration,
            "beep": True,
            "silence_timeout": 3,
            "callback_url": recording_callback_url,
        })

        return VoiceResponse(
            content=self._json_response(actions),
            content_type=self.get_content_type(),
        )

    async def fetch_recording(self, recording_url: str) -> RecordingData:
        """Fetch recording from Etisalat."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    recording_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "X-Account-ID": self.account_id,
                    },
                    follow_redirects=True,
                    timeout=30.0,
                )
                response.raise_for_status()

                # Determine format from content-type or URL
                content_type = response.headers.get("content-type", "")
                if "wav" in content_type or recording_url.endswith(".wav"):
                    audio_format = "wav"
                else:
                    audio_format = "mp3"

                return RecordingData(
                    audio_data=response.content,
                    audio_format=audio_format,
                )
        except httpx.HTTPError as e:
            raise VoiceProviderError(f"Failed to fetch Etisalat recording: {str(e)}")

    def parse_incoming_call(self, request_data: dict) -> dict:
        """Parse Etisalat incoming call webhook."""
        # Etisalat uses JSON format
        return {
            "call_sid": request_data.get("call_id", ""),
            "caller_id": request_data.get("from", ""),
            "called_number": request_data.get("to", ""),
            "direction": request_data.get("direction", "inbound"),
            "caller_country": request_data.get("from_country"),
        }

    def parse_recording_complete(self, request_data: dict) -> dict:
        """Parse Etisalat recording complete webhook."""
        return {
            "call_sid": request_data.get("call_id", ""),
            "recording_url": request_data.get("recording_url", ""),
            "recording_id": request_data.get("recording_id", ""),
            "recording_duration": int(request_data.get("duration", 0)),
        }

    def validate_webhook_signature(
        self,
        request_url: str,
        request_body: dict,
        signature: str,
    ) -> bool:
        """
        Validate Etisalat webhook signature.

        Uses HMAC-SHA256 for signature validation.
        """
        if not self.webhook_secret:
            # If no webhook secret configured, skip validation
            return True

        # Build signature payload
        payload = json.dumps(request_body, sort_keys=True, separators=(",", ":"))

        # Compute expected signature
        expected_signature = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)

    def _get_voice_for_language(self, language: str) -> str:
        """Get appropriate voice for language."""
        voice_mapping = {
            "en-US": "en-US-female",
            "en-GB": "en-GB-female",
            "ar-AE": "ar-AE-female",
            "ar-SA": "ar-SA-female",
            "hi-IN": "hi-IN-female",
        }
        return voice_mapping.get(language, "en-US-female")
