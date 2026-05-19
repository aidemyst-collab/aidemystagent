"""
Stripe webhook handler for AgentStudio.

Processes subscription lifecycle events and syncs plan state to:
  - OrgSubscription (Stripe fields + plan/status)
  - Organization.subscription_plan_id (FK to subscription_plans table)
  - Organization.subscription_status

The Organisation.subscription_plan_id update ensures that the next
build_token_claims() call (login or refresh) picks up the new products[].
"""
import stripe
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import logger
from app.models.billing import OrgSubscription, StripeWebhookEvent
from app.models.user import Organization
from app.models.subscription import SubscriptionPlan


async def handle_webhook(
    body: bytes,
    signature: str,
    db: AsyncSession,
) -> dict:
    # 1. Verify Stripe signature
    try:
        event = stripe.Webhook.construct_event(
            body, signature, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"[Webhook] Verified event {event.id} type={event.type}")
    except stripe.error.SignatureVerificationError as exc:
        logger.error(f"[Webhook] Signature verification failed: {exc}")
        return {"ok": False, "error": "invalid_signature"}

    # 2. Idempotency guard
    record = StripeWebhookEvent(
        stripe_event_id=event.id,
        event_type=event.type,
        payload=body.decode("utf-8"),
    )
    try:
        db.add(record)
        await db.flush()
    except Exception as exc:
        if "stripe_webhook_events_stripe_event_id" in str(exc) or "unique" in str(exc).lower():
            logger.info(f"[Webhook] Duplicate event {event.id} — skipping")
            await db.rollback()
            return {"ok": True, "skipped": True}
        raise

    # 3. Route
    error: Optional[str] = None
    try:
        if event.type == "checkout.session.completed":
            await _handle_checkout_completed(event, db)
        elif event.type in ("customer.subscription.created", "customer.subscription.updated"):
            await _handle_subscription_updated(event, db)
        elif event.type == "customer.subscription.deleted":
            await _handle_subscription_deleted(event, db)
        elif event.type == "invoice.payment_succeeded":
            await _handle_payment_succeeded(event, db)
        elif event.type == "invoice.payment_failed":
            await _handle_payment_failed(event, db)
        else:
            logger.info(f"[Webhook] Unhandled event type={event.type}")
    except Exception as exc:
        error = str(exc)
        logger.error(f"[Webhook] Error processing {event.id}: {exc}")

    record.processed = True
    record.processed_at = datetime.utcnow()
    record.error = error
    await db.commit()

    return {"ok": True}


# ── Event handlers ────────────────────────────────────────────────────────────

async def _handle_checkout_completed(event, db: AsyncSession) -> None:
    session = event.data.object
    org_id_str = (session.metadata or {}).get("org_id")
    if not org_id_str:
        logger.warning(f"[Webhook] checkout.session.completed missing org_id in metadata")
        return

    logger.info(f"[Webhook] checkout.session.completed org={org_id_str} sub={session.subscription}")

    sub = await _get_or_create_subscription(org_id_str, session.customer, db)
    sub.stripe_subscription_id = session.subscription
    sub.status = "active"

    if session.subscription:
        stripe_sub = stripe.Subscription.retrieve(session.subscription)
        _sync_from_stripe_sub(sub, stripe_sub)

    await _sync_org_plan(org_id_str, sub.plan, db)
    await db.flush()
    logger.info(f"[Webhook] Plan upgraded for org={org_id_str} → plan={sub.plan}")


async def _handle_subscription_updated(event, db: AsyncSession) -> None:
    stripe_sub = event.data.object
    price_id = (stripe_sub.items.data[0].price.id if stripe_sub.items and stripe_sub.items.data else None)
    logger.info(f"[Webhook] subscription.updated sub={stripe_sub.id} customer={stripe_sub.customer} status={stripe_sub.status} price={price_id}")

    sub = await db.scalar(
        select(OrgSubscription).where(OrgSubscription.stripe_subscription_id == stripe_sub.id)
    )
    if sub is None:
        sub = await db.scalar(
            select(OrgSubscription).where(OrgSubscription.stripe_customer_id == stripe_sub.customer)
        )
        if sub is None:
            logger.warning(f"[Webhook] subscription.updated — no record for sub={stripe_sub.id}")
            return
        sub.stripe_subscription_id = stripe_sub.id

    _sync_from_stripe_sub(sub, stripe_sub)
    await _sync_org_plan(str(sub.organization_id), sub.plan, db)
    await db.flush()


async def _handle_subscription_deleted(event, db: AsyncSession) -> None:
    stripe_sub = event.data.object
    sub = await db.scalar(
        select(OrgSubscription).where(OrgSubscription.stripe_subscription_id == stripe_sub.id)
    )
    if sub is None:
        logger.warning(f"[Webhook] subscription.deleted — no record for sub={stripe_sub.id}")
        return

    sub.plan = "free"
    sub.status = "canceled"
    sub.stripe_subscription_id = None
    sub.stripe_price_id = None
    sub.cancel_at_period_end = False
    sub.canceled_at = datetime.utcnow()
    await _sync_org_plan(str(sub.organization_id), "free", db)
    await db.flush()
    logger.info(f"[Webhook] subscription.deleted org={sub.organization_id} → free")


async def _handle_payment_succeeded(event, db: AsyncSession) -> None:
    invoice = event.data.object
    if not invoice.subscription:
        return

    sub = await db.scalar(
        select(OrgSubscription).where(OrgSubscription.stripe_subscription_id == invoice.subscription)
    )
    if sub is None:
        return

    sub.status = "active"
    sub.payment_failure_count = 0
    if invoice.lines and invoice.lines.data:
        line = invoice.lines.data[0]
        if line.period:
            sub.current_period_start = datetime.utcfromtimestamp(line.period.start) if line.period.start else None
            sub.current_period_end = datetime.utcfromtimestamp(line.period.end) if line.period.end else None

    await _sync_org_plan(str(sub.organization_id), sub.plan, db)
    await db.flush()


async def _handle_payment_failed(event, db: AsyncSession) -> None:
    invoice = event.data.object
    if not invoice.subscription:
        return

    sub = await db.scalar(
        select(OrgSubscription).where(OrgSubscription.stripe_subscription_id == invoice.subscription)
    )
    if sub is None:
        return

    sub.payment_failure_count += 1
    sub.status = "past_due"

    if sub.payment_failure_count >= 3:
        org = await db.scalar(select(Organization).where(Organization.id == sub.organization_id))
        if org:
            org.subscription_status = "suspended"
            logger.warning(f"[Webhook] Org {sub.organization_id} suspended after 3 payment failures")

    await db.flush()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_create_subscription(
    org_id_str: str,
    stripe_customer_id: str,
    db: AsyncSession,
) -> OrgSubscription:
    from uuid import UUID
    org_id = UUID(org_id_str)
    sub = await db.scalar(
        select(OrgSubscription).where(OrgSubscription.organization_id == org_id)
    )
    if sub is None:
        sub = OrgSubscription(
            organization_id=org_id,
            stripe_customer_id=stripe_customer_id,
        )
        db.add(sub)
    else:
        if not sub.stripe_customer_id:
            sub.stripe_customer_id = stripe_customer_id
    return sub


def _sync_from_stripe_sub(sub: OrgSubscription, stripe_sub) -> None:
    sub.stripe_subscription_id = stripe_sub.id
    sub.status = stripe_sub.status
    sub.cancel_at_period_end = stripe_sub.cancel_at_period_end
    sub.canceled_at = datetime.utcfromtimestamp(stripe_sub.canceled_at) if stripe_sub.canceled_at else None
    sub.trial_end = datetime.utcfromtimestamp(stripe_sub.trial_end) if stripe_sub.trial_end else None
    sub.current_period_start = datetime.utcfromtimestamp(stripe_sub.current_period_start) if stripe_sub.current_period_start else None
    sub.current_period_end = datetime.utcfromtimestamp(stripe_sub.current_period_end) if stripe_sub.current_period_end else None

    price_id = stripe_sub.items.data[0].price.id if stripe_sub.items and stripe_sub.items.data else None
    sub.stripe_price_id = price_id
    derived = _derive_plan(price_id, stripe_sub)
    if derived:
        sub.plan = derived


def _derive_plan(price_id: Optional[str], stripe_sub) -> Optional[str]:
    cfg = settings

    # 1. Nickname match
    nickname = ""
    if stripe_sub.items and stripe_sub.items.data:
        nickname = (stripe_sub.items.data[0].price.nickname or "").lower()

    if "enterprise" in nickname:
        return "enterprise"
    if "professional" in nickname:
        return "professional"
    if "starter" in nickname:
        return "starter"

    # 2. Price ID match
    if price_id:
        if price_id in (cfg.STRIPE_PRICE_ENTERPRISE_MONTHLY, cfg.STRIPE_PRICE_ENTERPRISE_ANNUAL):
            return "enterprise"
        if price_id in (cfg.STRIPE_PRICE_PROFESSIONAL_MONTHLY, cfg.STRIPE_PRICE_PROFESSIONAL_ANNUAL):
            return "professional"
        if price_id in (cfg.STRIPE_PRICE_STARTER_MONTHLY, cfg.STRIPE_PRICE_STARTER_ANNUAL):
            return "starter"

    logger.error(f"[Webhook] Plan derivation failed — priceId={price_id} nickname='{nickname}'")
    return None


async def _sync_org_plan(org_id_str: str, plan_name: str, db: AsyncSession) -> None:
    """Update Organization.subscription_plan_id + subscription_status so build_token_claims picks up the new products."""
    from uuid import UUID
    org_id = UUID(org_id_str)

    org = await db.scalar(select(Organization).where(Organization.id == org_id))
    if not org:
        logger.error(f"[Webhook] _sync_org_plan: org {org_id} not found")
        return

    # Find matching SubscriptionPlan row
    plan_row = await db.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.name == plan_name)
    )
    if plan_row:
        org.subscription_plan_id = plan_row.id
    else:
        logger.warning(f"[Webhook] No SubscriptionPlan row found for name='{plan_name}'")

    org.subscription_status = "active" if plan_name != "free" else "trial"
    logger.info(f"[Webhook] Org {org_id} synced → plan={plan_name} status={org.subscription_status}")
