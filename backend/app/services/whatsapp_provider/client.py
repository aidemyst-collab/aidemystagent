"""
WhatsApp Cloud API Client

Handles sending messages via Meta Graph API.
"""

import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v19.0"
GRAPH_API_BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class WhatsAppError(Exception):
    """WhatsApp API error."""

    def __init__(self, message: str, error_code: Optional[int] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class WhatsAppClient:
    """
    WhatsApp Cloud API client for sending messages.

    Usage:
        client = WhatsAppClient(
            phone_number_id="1234567890",
            access_token="your_access_token"
        )
        await client.send_text_message("+1234567890", "Hello!")
    """

    def __init__(
        self,
        phone_number_id: str,
        access_token: str,
        business_account_id: Optional[str] = None,
    ):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.business_account_id = business_account_id
        self.base_url = f"{GRAPH_API_BASE_URL}/{phone_number_id}"

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def send_text_message(
        self,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> Dict[str, Any]:
        """
        Send a text message.

        Args:
            to: Recipient phone number (with country code, no +)
            text: Message text (max 4096 characters)
            preview_url: Enable URL preview

        Returns:
            API response with message ID
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to.replace("+", ""),
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text[:4096],  # Max 4096 chars
            },
        }

        return await self._send_message(payload)

    async def send_media_message(
        self,
        to: str,
        media_type: str,  # image, video, audio, document
        media_url: Optional[str] = None,
        media_id: Optional[str] = None,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a media message.

        Args:
            to: Recipient phone number
            media_type: Type of media (image, video, audio, document)
            media_url: URL of the media (either url or id required)
            media_id: Media ID from uploaded media
            caption: Optional caption (for image, video, document)
            filename: Filename for document type

        Returns:
            API response with message ID
        """
        if not media_url and not media_id:
            raise WhatsAppError("Either media_url or media_id is required")

        media_object: Dict[str, Any] = {}
        if media_url:
            media_object["link"] = media_url
        if media_id:
            media_object["id"] = media_id
        if caption and media_type in ["image", "video", "document"]:
            media_object["caption"] = caption[:1024]  # Max 1024 chars
        if filename and media_type == "document":
            media_object["filename"] = filename

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to.replace("+", ""),
            "type": media_type,
            media_type: media_object,
        }

        return await self._send_message(payload)

    async def send_template_message(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Send a template message.

        Template messages can be sent outside the 24-hour window.
        Templates must be pre-approved by Meta.

        Args:
            to: Recipient phone number
            template_name: Name of the approved template
            language_code: Template language code (e.g., "en", "en_US")
            components: Template components (header, body, buttons variables)

        Returns:
            API response with message ID
        """
        template_object: Dict[str, Any] = {
            "name": template_name,
            "language": {
                "code": language_code,
            },
        }

        if components:
            template_object["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to.replace("+", ""),
            "type": "template",
            "template": template_object,
        }

        return await self._send_message(payload)

    async def send_interactive_message(
        self,
        to: str,
        interactive_type: str,  # button, list
        body_text: str,
        action: Dict[str, Any],
        header: Optional[Dict] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an interactive message with buttons or lists.

        Args:
            to: Recipient phone number
            interactive_type: Type (button, list)
            body_text: Main message body
            action: Action object (buttons or sections)
            header: Optional header (text, image, video, document)
            footer: Optional footer text

        Returns:
            API response with message ID
        """
        interactive_object: Dict[str, Any] = {
            "type": interactive_type,
            "body": {
                "text": body_text[:1024],
            },
            "action": action,
        }

        if header:
            interactive_object["header"] = header
        if footer:
            interactive_object["footer"] = {"text": footer[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to.replace("+", ""),
            "type": "interactive",
            "interactive": interactive_object,
        }

        return await self._send_message(payload)

    async def send_reaction(
        self,
        to: str,
        message_id: str,
        emoji: str,
    ) -> Dict[str, Any]:
        """
        Send a reaction to a message.

        Args:
            to: Recipient phone number
            message_id: ID of message to react to
            emoji: Emoji character

        Returns:
            API response
        """
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to.replace("+", ""),
            "type": "reaction",
            "reaction": {
                "message_id": message_id,
                "emoji": emoji,
            },
        }

        return await self._send_message(payload)

    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark a message as read.

        Args:
            message_id: ID of the message to mark as read

        Returns:
            API response
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        return await self._send_message(payload)

    async def upload_media(
        self,
        file_data: bytes,
        mime_type: str,
        filename: str,
    ) -> str:
        """
        Upload media to WhatsApp servers.

        Args:
            file_data: Raw file bytes
            mime_type: MIME type of the file
            filename: Name of the file

        Returns:
            Media ID for use in messages
        """
        url = f"{GRAPH_API_BASE_URL}/{self.phone_number_id}/media"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                files={
                    "file": (filename, file_data, mime_type),
                },
                data={
                    "messaging_product": "whatsapp",
                    "type": mime_type,
                },
                timeout=60.0,
            )

            if response.status_code != 200:
                error_data = response.json()
                raise WhatsAppError(
                    f"Media upload failed: {error_data}",
                    error_code=response.status_code,
                )

            return response.json()["id"]

    async def get_media_url(self, media_id: str) -> str:
        """
        Get download URL for a media file.

        Args:
            media_id: Media ID from incoming message

        Returns:
            Temporary download URL
        """
        url = f"{GRAPH_API_BASE_URL}/{media_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                timeout=30.0,
            )

            if response.status_code != 200:
                raise WhatsAppError(f"Failed to get media URL: {response.text}")

            return response.json()["url"]

    async def download_media(self, media_url: str) -> bytes:
        """
        Download media file from WhatsApp servers.

        Args:
            media_url: URL from get_media_url()

        Returns:
            Raw file bytes
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                media_url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=60.0,
            )

            if response.status_code != 200:
                raise WhatsAppError(
                    f"Failed to download media: {response.status_code}"
                )

            return response.content

    async def get_templates(self) -> List[Dict[str, Any]]:
        """
        Get list of message templates for the business account.

        Returns:
            List of template objects
        """
        if not self.business_account_id:
            raise WhatsAppError(
                "Business account ID required for template management"
            )

        url = f"{GRAPH_API_BASE_URL}/{self.business_account_id}/message_templates"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self._get_headers(),
                timeout=30.0,
            )

            if response.status_code != 200:
                raise WhatsAppError(f"Failed to get templates: {response.text}")

            return response.json().get("data", [])

    async def _send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to send message via Graph API.
        """
        url = f"{self.base_url}/messages"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30.0,
            )

            response_data = response.json()

            if response.status_code != 200:
                error = response_data.get("error", {})
                raise WhatsAppError(
                    message=error.get("message", "Unknown error"),
                    error_code=error.get("code"),
                )

            logger.info(f"Message sent: {response_data}")
            return response_data
