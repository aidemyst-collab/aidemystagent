"""
WhatsApp Message Types

Pydantic models for incoming and outgoing WhatsApp messages.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from enum import Enum
from datetime import datetime


class MessageType(str, Enum):
    """WhatsApp message types."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    BUTTON = "button"
    TEMPLATE = "template"
    REACTION = "reaction"
    ORDER = "order"
    UNKNOWN = "unknown"


class TextMessage(BaseModel):
    """Text message content."""
    body: str = Field(..., max_length=4096)
    preview_url: bool = False


class MediaMessage(BaseModel):
    """Media message content (image, video, audio, document)."""
    media_type: str  # image, video, audio, document
    media_id: Optional[str] = None
    media_url: Optional[str] = None
    caption: Optional[str] = Field(None, max_length=1024)
    filename: Optional[str] = None  # For documents
    mime_type: Optional[str] = None
    sha256: Optional[str] = None


class LocationMessage(BaseModel):
    """Location message content."""
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None


class ContactInfo(BaseModel):
    """Contact information."""
    name: Dict[str, str]  # formatted_name, first_name, last_name, etc.
    phones: Optional[List[Dict[str, str]]] = None
    emails: Optional[List[Dict[str, str]]] = None
    addresses: Optional[List[Dict[str, str]]] = None
    org: Optional[Dict[str, str]] = None
    urls: Optional[List[Dict[str, str]]] = None


class ContactsMessage(BaseModel):
    """Contacts message content."""
    contacts: List[ContactInfo]


class InteractiveButton(BaseModel):
    """Interactive button."""
    id: str = Field(..., max_length=256)
    title: str = Field(..., max_length=20)


class InteractiveListRow(BaseModel):
    """Interactive list row."""
    id: str = Field(..., max_length=200)
    title: str = Field(..., max_length=24)
    description: Optional[str] = Field(None, max_length=72)


class InteractiveListSection(BaseModel):
    """Interactive list section."""
    title: Optional[str] = Field(None, max_length=24)
    rows: List[InteractiveListRow] = Field(..., max_length=10)


class InteractiveMessage(BaseModel):
    """Interactive message content (buttons or list)."""
    type: str  # button, list, product, product_list
    header: Optional[Dict[str, Any]] = None  # text, image, video, document
    body: str = Field(..., max_length=1024)
    footer: Optional[str] = Field(None, max_length=60)

    # For button type
    buttons: Optional[List[InteractiveButton]] = Field(None, max_length=3)

    # For list type
    button_text: Optional[str] = Field(None, max_length=20)  # List button label
    sections: Optional[List[InteractiveListSection]] = Field(None, max_length=10)


class TemplateComponent(BaseModel):
    """Template component for variable substitution."""
    type: str  # header, body, button
    sub_type: Optional[str] = None  # For buttons: quick_reply, url
    index: Optional[int] = None  # Button index
    parameters: List[Dict[str, Any]] = []


class TemplateMessage(BaseModel):
    """Template message content."""
    name: str
    language_code: str = "en"
    components: Optional[List[TemplateComponent]] = None


class ReactionMessage(BaseModel):
    """Reaction to a message."""
    message_id: str
    emoji: str


class ButtonReply(BaseModel):
    """Button reply from user."""
    id: str
    title: str


class ListReply(BaseModel):
    """List selection reply from user."""
    id: str
    title: str
    description: Optional[str] = None


class InteractiveReply(BaseModel):
    """Interactive message reply."""
    type: str  # button_reply, list_reply
    button_reply: Optional[ButtonReply] = None
    list_reply: Optional[ListReply] = None


class MessageContext(BaseModel):
    """Context for replied/forwarded messages."""
    message_id: str
    from_number: Optional[str] = None
    forwarded: bool = False
    frequently_forwarded: bool = False


class IncomingMessage(BaseModel):
    """
    Parsed incoming WhatsApp message from webhook.

    This is a unified model that captures all incoming message types.
    """
    # Message identification
    message_id: str
    timestamp: datetime

    # Sender information
    from_number: str  # Phone number with country code
    from_name: Optional[str] = None  # Profile name if available

    # Message type
    message_type: MessageType

    # Content (one of these will be populated based on type)
    text: Optional[TextMessage] = None
    media: Optional[MediaMessage] = None
    location: Optional[LocationMessage] = None
    contacts: Optional[ContactsMessage] = None
    interactive: Optional[InteractiveReply] = None
    button: Optional[ButtonReply] = None  # Quick reply button
    reaction: Optional[ReactionMessage] = None

    # Context (for replies/forwards)
    context: Optional[MessageContext] = None

    # Raw data for debugging
    raw_data: Optional[Dict[str, Any]] = None

    @classmethod
    def from_webhook_payload(cls, message: Dict, contact: Dict) -> "IncomingMessage":
        """
        Parse incoming message from webhook payload.

        Args:
            message: The message object from webhook
            contact: The contact object from webhook

        Returns:
            Parsed IncomingMessage
        """
        msg_id = message.get("id", "")
        timestamp = datetime.fromtimestamp(int(message.get("timestamp", 0)))
        from_number = message.get("from", "")
        from_name = contact.get("profile", {}).get("name")
        msg_type_str = message.get("type", "unknown")

        try:
            msg_type = MessageType(msg_type_str)
        except ValueError:
            msg_type = MessageType.UNKNOWN

        # Parse content based on type
        text = None
        media = None
        location = None
        contacts = None
        interactive = None
        button = None
        reaction = None

        if msg_type == MessageType.TEXT:
            text_data = message.get("text", {})
            text = TextMessage(body=text_data.get("body", ""))

        elif msg_type in [MessageType.IMAGE, MessageType.VIDEO,
                          MessageType.AUDIO, MessageType.DOCUMENT,
                          MessageType.STICKER]:
            media_data = message.get(msg_type_str, {})
            media = MediaMessage(
                media_type=msg_type_str,
                media_id=media_data.get("id"),
                mime_type=media_data.get("mime_type"),
                sha256=media_data.get("sha256"),
                caption=media_data.get("caption"),
                filename=media_data.get("filename"),
            )

        elif msg_type == MessageType.LOCATION:
            loc_data = message.get("location", {})
            location = LocationMessage(
                latitude=loc_data.get("latitude", 0),
                longitude=loc_data.get("longitude", 0),
                name=loc_data.get("name"),
                address=loc_data.get("address"),
            )

        elif msg_type == MessageType.CONTACTS:
            contacts_data = message.get("contacts", [])
            contact_list = []
            for c in contacts_data:
                contact_list.append(ContactInfo(
                    name=c.get("name", {}),
                    phones=c.get("phones"),
                    emails=c.get("emails"),
                    addresses=c.get("addresses"),
                    org=c.get("org"),
                    urls=c.get("urls"),
                ))
            contacts = ContactsMessage(contacts=contact_list)

        elif msg_type == MessageType.INTERACTIVE:
            interactive_data = message.get("interactive", {})
            int_type = interactive_data.get("type")

            if int_type == "button_reply":
                btn = interactive_data.get("button_reply", {})
                interactive = InteractiveReply(
                    type="button_reply",
                    button_reply=ButtonReply(
                        id=btn.get("id", ""),
                        title=btn.get("title", ""),
                    ),
                )
            elif int_type == "list_reply":
                lst = interactive_data.get("list_reply", {})
                interactive = InteractiveReply(
                    type="list_reply",
                    list_reply=ListReply(
                        id=lst.get("id", ""),
                        title=lst.get("title", ""),
                        description=lst.get("description"),
                    ),
                )

        elif msg_type == MessageType.BUTTON:
            btn_data = message.get("button", {})
            button = ButtonReply(
                id=btn_data.get("payload", ""),
                title=btn_data.get("text", ""),
            )

        elif msg_type == MessageType.REACTION:
            react_data = message.get("reaction", {})
            reaction = ReactionMessage(
                message_id=react_data.get("message_id", ""),
                emoji=react_data.get("emoji", ""),
            )

        # Parse context if present
        context = None
        if "context" in message:
            ctx = message["context"]
            context = MessageContext(
                message_id=ctx.get("id", ""),
                from_number=ctx.get("from"),
                forwarded=ctx.get("forwarded", False),
                frequently_forwarded=ctx.get("frequently_forwarded", False),
            )

        return cls(
            message_id=msg_id,
            timestamp=timestamp,
            from_number=from_number,
            from_name=from_name,
            message_type=msg_type,
            text=text,
            media=media,
            location=location,
            contacts=contacts,
            interactive=interactive,
            button=button,
            reaction=reaction,
            context=context,
            raw_data=message,
        )


class OutgoingMessage(BaseModel):
    """
    Outgoing message to be sent via WhatsApp.

    Use the appropriate field based on message type.
    """
    to: str  # Recipient phone number
    message_type: MessageType

    # Content (one of these should be populated)
    text: Optional[TextMessage] = None
    media: Optional[MediaMessage] = None
    location: Optional[LocationMessage] = None
    contacts: Optional[ContactsMessage] = None
    interactive: Optional[InteractiveMessage] = None
    template: Optional[TemplateMessage] = None
    reaction: Optional[ReactionMessage] = None

    # Optional: reply to a specific message
    reply_to_message_id: Optional[str] = None


class WebhookMessage(BaseModel):
    """
    Webhook payload entry for a single message event.
    """
    messaging_product: str = "whatsapp"
    metadata: Dict[str, str]  # display_phone_number, phone_number_id
    contacts: List[Dict[str, Any]]
    messages: List[Dict[str, Any]]


class WebhookStatus(BaseModel):
    """
    Webhook payload for message status updates.
    """
    id: str  # Message ID
    status: str  # sent, delivered, read, failed
    timestamp: datetime
    recipient_id: str
    conversation: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None


class WebhookPayload(BaseModel):
    """
    Complete webhook payload from WhatsApp.
    """
    object: str = "whatsapp_business_account"
    entry: List[Dict[str, Any]]

    def get_messages(self) -> List[IncomingMessage]:
        """Extract all messages from the webhook payload."""
        messages = []

        for entry in self.entry:
            changes = entry.get("changes", [])
            for change in changes:
                if change.get("field") != "messages":
                    continue

                value = change.get("value", {})
                contacts = value.get("contacts", [{}])
                msgs = value.get("messages", [])

                for msg in msgs:
                    contact = contacts[0] if contacts else {}
                    messages.append(
                        IncomingMessage.from_webhook_payload(msg, contact)
                    )

        return messages

    def get_statuses(self) -> List[WebhookStatus]:
        """Extract all status updates from the webhook payload."""
        statuses = []

        for entry in self.entry:
            changes = entry.get("changes", [])
            for change in changes:
                if change.get("field") != "messages":
                    continue

                value = change.get("value", {})
                status_list = value.get("statuses", [])

                for status in status_list:
                    statuses.append(WebhookStatus(
                        id=status.get("id", ""),
                        status=status.get("status", ""),
                        timestamp=datetime.fromtimestamp(
                            int(status.get("timestamp", 0))
                        ),
                        recipient_id=status.get("recipient_id", ""),
                        conversation=status.get("conversation"),
                        pricing=status.get("pricing"),
                        errors=status.get("errors"),
                    ))

        return statuses
