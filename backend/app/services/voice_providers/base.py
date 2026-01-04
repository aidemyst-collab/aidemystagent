"""
Base Voice Provider Abstract Class

All voice providers must inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass


class VoiceProviderError(Exception):
    """Base exception for voice provider errors."""
    pass


@dataclass
class VoiceResponse:
    """Standard voice response structure."""
    content: str
    content_type: str
    session_id: Optional[str] = None


@dataclass
class RecordingData:
    """Recording data from voice provider."""
    audio_data: bytes
    audio_format: str
    duration: Optional[float] = None
    caller_id: Optional[str] = None
    call_sid: Optional[str] = None


class VoiceProvider(ABC):
    """
    Abstract base class for voice providers.

    All voice providers (Twilio, Etisalat) must implement this interface.
    """

    provider_name: str = "base"

    def __init__(self, credentials: dict):
        """
        Initialize the voice provider with credentials.

        Args:
            credentials: Provider-specific credentials dictionary
        """
        self.credentials = credentials
        self._validate_credentials()

    @abstractmethod
    def _validate_credentials(self) -> None:
        """
        Validate that required credentials are present.

        Raises:
            VoiceProviderError: If credentials are invalid or missing
        """
        pass

    @abstractmethod
    def get_content_type(self) -> str:
        """
        Get the content type for responses.

        Returns:
            Content type string (e.g., 'application/xml' for Twilio)
        """
        pass

    @abstractmethod
    def generate_greeting_response(
        self,
        greeting: str,
        recording_callback_url: str,
        language: str = "en-US",
        max_duration: int = 60,
        play_beep: bool = True,
    ) -> VoiceResponse:
        """
        Generate response to play greeting and start recording.

        Args:
            greeting: Text to speak as greeting
            recording_callback_url: URL to receive recording data
            language: Language code for TTS
            max_duration: Maximum recording duration in seconds
            play_beep: Whether to play beep before recording

        Returns:
            VoiceResponse with provider-specific format
        """
        pass

    @abstractmethod
    def generate_audio_response(
        self,
        audio_url: str,
        after_action: str = "hangup",
        transfer_to: Optional[str] = None,
        loop: int = 1,
    ) -> VoiceResponse:
        """
        Generate response to play audio.

        Args:
            audio_url: URL of audio file to play
            after_action: Action after playing ('hangup', 'continue', 'transfer')
            transfer_to: Phone number to transfer to (if after_action is 'transfer')
            loop: Number of times to loop the audio

        Returns:
            VoiceResponse with provider-specific format
        """
        pass

    @abstractmethod
    def generate_text_response(
        self,
        text: str,
        voice: str = "alice",
        language: str = "en-US",
        after_action: str = "hangup",
    ) -> VoiceResponse:
        """
        Generate response to speak text.

        Args:
            text: Text to speak
            voice: Voice name to use
            language: Language code
            after_action: Action after speaking

        Returns:
            VoiceResponse with provider-specific format
        """
        pass

    @abstractmethod
    def generate_hangup_response(
        self,
        goodbye_message: Optional[str] = None,
        language: str = "en-US",
    ) -> VoiceResponse:
        """
        Generate response to hang up the call.

        Args:
            goodbye_message: Optional message to play before hanging up
            language: Language code for TTS

        Returns:
            VoiceResponse with provider-specific format
        """
        pass

    @abstractmethod
    def generate_continue_response(
        self,
        recording_callback_url: str,
        prompt: Optional[str] = None,
        language: str = "en-US",
        max_duration: int = 60,
    ) -> VoiceResponse:
        """
        Generate response to continue conversation (record again).

        Args:
            recording_callback_url: URL to receive next recording
            prompt: Optional prompt to speak before recording
            language: Language code
            max_duration: Max recording duration

        Returns:
            VoiceResponse with provider-specific format
        """
        pass

    @abstractmethod
    async def fetch_recording(self, recording_url: str) -> RecordingData:
        """
        Fetch recording audio from provider.

        Args:
            recording_url: URL of the recording

        Returns:
            RecordingData with audio bytes and metadata

        Raises:
            VoiceProviderError: If fetching fails
        """
        pass

    @abstractmethod
    def parse_incoming_call(self, request_data: dict) -> dict:
        """
        Parse incoming call webhook data.

        Args:
            request_data: Raw webhook data from provider

        Returns:
            Normalized call data dictionary with:
                - call_sid: Unique call identifier
                - caller_id: Caller phone number
                - called_number: Called phone number
                - direction: 'inbound' or 'outbound'
        """
        pass

    @abstractmethod
    def parse_recording_complete(self, request_data: dict) -> dict:
        """
        Parse recording complete webhook data.

        Args:
            request_data: Raw webhook data from provider

        Returns:
            Normalized recording data dictionary with:
                - call_sid: Call identifier
                - recording_url: URL to fetch recording
                - recording_duration: Duration in seconds
        """
        pass

    @abstractmethod
    def validate_webhook_signature(
        self,
        request_url: str,
        request_body: dict,
        signature: str,
    ) -> bool:
        """
        Validate webhook signature for security.

        Args:
            request_url: Full URL of the webhook request
            request_body: Request body/parameters
            signature: Signature header value

        Returns:
            True if signature is valid, False otherwise
        """
        pass
