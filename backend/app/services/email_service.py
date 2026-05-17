"""
Email service for AgentStudio.
Uses Azure Communication Services (ACS) Email SDK for delivery.
"""
from typing import Optional

from azure.communication.email.aio import EmailClient

from app.core.config import settings
from app.core.logging_config import logger


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """
    Send an email via Azure Communication Services.
    Returns True on success, False on failure.
    Never raises — failures are logged and suppressed.
    """
    if not settings.EMAIL_ENABLED:
        logger.info(f"Email disabled — would have sent '{subject}' to {to_email}")
        return False

    if not settings.ACS_CONNECTION_STRING:
        logger.warning("ACS_CONNECTION_STRING not configured — skipping email send")
        return False

    try:
        message = {
            "senderAddress": settings.ACS_SENDER_ADDRESS,
            "recipients": {
                "to": [{"address": to_email}],
            },
            "content": {
                "subject": subject,
                "html": html_body,
                **({"plainText": text_body} if text_body else {}),
            },
        }

        async with EmailClient.from_connection_string(settings.ACS_CONNECTION_STRING) as client:
            poller = await client.begin_send(message)
            await poller.result()

        logger.info(f"Email sent via ACS: '{subject}' → {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def send_invitation_email(
    to_email: str,
    inviter_name: str,
    org_name: str,
    role_name: str,
    token: str,
    personal_message: Optional[str] = None,
) -> bool:
    """Send an invitation email with the accept link."""
    accept_url = f"{settings.FRONTEND_URL}/invitations/accept/{token}"
    subject = f"You've been invited to join {org_name} on AgentStudio"

    personal_msg_block = ""
    if personal_message:
        personal_msg_block = f"""
        <tr>
          <td style="padding: 0 40px 20px;">
            <div style="background: #f8fafc; border-left: 3px solid #6366f1; padding: 12px 16px; border-radius: 4px;">
              <p style="margin: 0; color: #4b5563; font-style: italic;">"{personal_message}"</p>
            </div>
          </td>
        </tr>
        """

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="padding: 40px 20px;">
        <tr>
          <td align="center">
            <table width="560" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.07);">
              <!-- Header -->
              <tr>
                <td style="background: linear-gradient(135deg, #4338ca 0%, #6366f1 100%); padding: 32px 40px; text-align: center;">
                  <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700;">AgentStudio</h1>
                  <p style="margin: 8px 0 0; color: #c7d2fe; font-size: 14px;">AI Agent Creation Platform</p>
                </td>
              </tr>
              <!-- Body -->
              <tr>
                <td style="padding: 32px 40px 20px;">
                  <h2 style="margin: 0 0 12px; color: #111827; font-size: 20px;">You have been invited!</h2>
                  <p style="margin: 0 0 8px; color: #4b5563; line-height: 1.6;">
                    <strong>{inviter_name}</strong> has invited you to join <strong>{org_name}</strong> as a <strong>{role_name}</strong>.
                  </p>
                </td>
              </tr>
              {personal_msg_block}
              <!-- CTA -->
              <tr>
                <td style="padding: 8px 40px 32px; text-align: center;">
                  <a href="{accept_url}"
                     style="display: inline-block; padding: 14px 32px; background: #6366f1; color: #ffffff; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px;">
                    Accept Invitation
                  </a>
                  <p style="margin: 16px 0 0; color: #9ca3af; font-size: 12px;">
                    This link expires in 7 days. If you didn't expect this invitation, you can ignore this email.
                  </p>
                </td>
              </tr>
              <!-- Footer -->
              <tr>
                <td style="background: #f9fafb; padding: 16px 40px; border-top: 1px solid #e5e7eb;">
                  <p style="margin: 0; color: #9ca3af; font-size: 12px; text-align: center;">
                    Or copy this link: <a href="{accept_url}" style="color: #6366f1;">{accept_url}</a>
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    text_body = (
        f"You've been invited to join {org_name} on AgentStudio as a {role_name}.\n\n"
        f"Invited by: {inviter_name}\n"
        + (f"Message: {personal_message}\n\n" if personal_message else "\n")
        + f"Accept your invitation: {accept_url}\n\n"
        "This link expires in 7 days."
    )

    return await send_email(to_email, subject, html_body, text_body)
