"""
Stripe billing service for AgentStudio.

Handles subscription lifecycle: checkout sessions, customer portal,
cancel/reactivate, invoice retrieval, and plan catalogue.
"""
import stripe
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.logging_config import logger
from app.models.billing import OrgSubscription
from app.models.user import Organization

stripe.api_key = settings.STRIPE_SECRET_KEY

# ── Plan limits (mirrors subscription_plans table) ────────────────────────────

_PLAN_LIMITS = {
    "free":         {"max_users": 1,  "max_agents": 3,  "max_deployments": 1,  "max_executions": 200},
    "starter":      {"max_users": 5,  "max_agents": 15, "max_deployments": 5,  "max_executions": 2000},
    "professional": {"max_users": 20, "max_agents": 50, "max_deployments": 20, "max_executions": 10000},
    "enterprise":   {"max_users": -1, "max_agents": -1, "max_deployments": -1, "max_executions": -1},
}


# ── Pydantic-free response dicts (FastAPI serialises them fine) ───────────────

def _subscription_response(sub: Optional[OrgSubscription]) -> dict:
    if sub is None:
        limits = _PLAN_LIMITS["free"]
        return {
            "plan": "free",
            "status": "trialing",
            "stripe_subscription_id": None,
            "stripe_price_id": None,
            "current_period_end": None,
            "cancel_at_period_end": False,
            "trial_end": None,
            **limits,
        }
    limits = _PLAN_LIMITS.get(sub.plan.lower(), _PLAN_LIMITS["free"])
    return {
        "plan": sub.plan,
        "status": sub.status,
        "stripe_subscription_id": sub.stripe_subscription_id,
        "stripe_price_id": sub.stripe_price_id,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "trial_end": sub.trial_end.isoformat() if sub.trial_end else None,
        **limits,
    }


# ── Service functions ─────────────────────────────────────────────────────────

async def get_subscription(org_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(OrgSubscription).where(OrgSubscription.organization_id == org_id)
    )
    sub = result.scalar_one_or_none()
    return _subscription_response(sub)


async def create_checkout_session(
    org_id: UUID,
    price_id: str,
    success_url: str,
    cancel_url: str,
    db: AsyncSession,
) -> dict:
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise ValueError(f"Organisation {org_id} not found")

    result2 = await db.execute(
        select(OrgSubscription).where(OrgSubscription.organization_id == org_id)
    )
    existing = result2.scalar_one_or_none()

    # Block if already subscribed to the same price
    if existing and existing.status == "active" and existing.stripe_price_id == price_id:
        raise ValueError("Organisation already has an active subscription for this plan.")

    stripe_customer_id = await _get_or_create_customer(org_id, org, existing, db)

    session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata={"org_id": str(org_id), "price_id": price_id},
        idempotency_key=f"checkout-{org_id}-{price_id}-{datetime.utcnow().strftime('%Y%m%d%H')}",
    )
    return {"session_id": session.id, "url": session.url}


async def create_portal_session(org_id: UUID, return_url: str, db: AsyncSession) -> dict:
    result = await db.execute(
        select(OrgSubscription).where(OrgSubscription.organization_id == org_id)
    )
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_customer_id:
        raise ValueError("No billing record found for this organisation.")

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=return_url,
    )
    return {"url": session.url}


async def cancel_subscription(org_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(OrgSubscription).where(OrgSubscription.organization_id == org_id)
    )
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_subscription_id:
        raise ValueError("No active subscription to cancel.")

    updated = stripe.Subscription.modify(
        sub.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    sub.cancel_at_period_end = updated.cancel_at_period_end
    sub.updated_at = datetime.utcnow()
    await db.commit()
    return _subscription_response(sub)


async def reactivate_subscription(org_id: UUID, db: AsyncSession) -> dict:
    result = await db.execute(
        select(OrgSubscription).where(OrgSubscription.organization_id == org_id)
    )
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_subscription_id:
        raise ValueError("No active subscription to reactivate.")

    updated = stripe.Subscription.modify(
        sub.stripe_subscription_id,
        cancel_at_period_end=False,
    )
    sub.cancel_at_period_end = updated.cancel_at_period_end
    sub.updated_at = datetime.utcnow()
    await db.commit()
    return _subscription_response(sub)


async def get_invoices(org_id: UUID, limit: int, db: AsyncSession) -> dict:
    result = await db.execute(
        select(OrgSubscription).where(OrgSubscription.organization_id == org_id)
    )
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_customer_id:
        return {"invoices": [], "has_more": False}

    invoices = stripe.Invoice.list(customer=sub.stripe_customer_id, limit=limit)
    return {
        "invoices": [
            {
                "id": inv.id,
                "number": inv.number or "",
                "amount_paid": inv.amount_paid,
                "currency": inv.currency or "aed",
                "status": inv.status or "",
                "hosted_invoice_url": inv.hosted_invoice_url,
                "invoice_pdf": inv.invoice_pdf,
                "period_start": datetime.utcfromtimestamp(inv.period_start).isoformat() if inv.period_start else None,
                "period_end": datetime.utcfromtimestamp(inv.period_end).isoformat() if inv.period_end else None,
            }
            for inv in invoices.data
        ],
        "has_more": invoices.has_more,
    }


def get_plan_catalogue() -> dict:
    cfg = settings
    return {
        "plans": [
            {
                "key": "free",
                "name": "Free",
                "price_monthly_aed": 0,
                "price_annual_aed": 0,
                "stripe_price_id_monthly": "",
                "stripe_price_id_annual": "",
                "max_users": 1,
                "max_agents": 3,
                "max_deployments": 1,
                "max_executions": 200,
                "has_demystrag": False,
                "has_mock_api": False,
                "features": [
                    "1 user",
                    "3 AI Agents",
                    "200 executions/month",
                    "1 active deployment",
                    "Visual Workflow Builder",
                    "Community support",
                ],
            },
            {
                "key": "starter",
                "name": "Starter",
                "price_monthly_aed": 149,
                "price_annual_aed": 1490,
                "stripe_price_id_monthly": cfg.STRIPE_PRICE_STARTER_MONTHLY,
                "stripe_price_id_annual": cfg.STRIPE_PRICE_STARTER_ANNUAL,
                "max_users": 5,
                "max_agents": 15,
                "max_deployments": 5,
                "max_executions": 2000,
                "has_demystrag": False,
                "has_mock_api": False,
                "features": [
                    "5 users",
                    "15 AI Agents",
                    "2,000 executions/month",
                    "5 active deployments",
                    "All built-in tools",
                    "Custom tool creation",
                    "API access",
                    "Basic analytics",
                    "Email support",
                ],
            },
            {
                "key": "professional",
                "name": "Professional",
                "price_monthly_aed": 449,
                "price_annual_aed": 4490,
                "stripe_price_id_monthly": cfg.STRIPE_PRICE_PROFESSIONAL_MONTHLY,
                "stripe_price_id_annual": cfg.STRIPE_PRICE_PROFESSIONAL_ANNUAL,
                "max_users": 20,
                "max_agents": 50,
                "max_deployments": 20,
                "max_executions": 10000,
                "has_demystrag": True,
                "has_mock_api": True,
                "features": [
                    "20 users",
                    "50 AI Agents",
                    "10,000 executions/month",
                    "20 active deployments",
                    "Everything in Starter",
                    "DemystRAG — 2,000 documents, 20 GB",
                    "Mock API — configurable testing",
                    "Advanced analytics",
                    "Audit logs",
                    "Priority support",
                ],
            },
            {
                "key": "enterprise",
                "name": "Enterprise",
                "price_monthly_aed": 1299,
                "price_annual_aed": 12990,
                "stripe_price_id_monthly": cfg.STRIPE_PRICE_ENTERPRISE_MONTHLY,
                "stripe_price_id_annual": cfg.STRIPE_PRICE_ENTERPRISE_ANNUAL,
                "max_users": -1,
                "max_agents": -1,
                "max_deployments": -1,
                "max_executions": -1,
                "has_demystrag": True,
                "has_mock_api": True,
                "features": [
                    "Unlimited users",
                    "Unlimited AI Agents",
                    "Unlimited executions",
                    "Unlimited deployments",
                    "Everything in Professional",
                    "DemystRAG — unlimited docs & storage",
                    "Mock API — full access",
                    "All embedding providers",
                    "SSO & custom branding",
                    "Dedicated account manager",
                    "SLA guarantee",
                ],
            },
        ]
    }


# ── Private helpers ───────────────────────────────────────────────────────────

async def _get_or_create_customer(
    org_id: UUID,
    org: Organization,
    existing: Optional[OrgSubscription],
    db: AsyncSession,
) -> str:
    if existing and existing.stripe_customer_id:
        return existing.stripe_customer_id

    # Find owner email for the customer record
    from app.models.user import User
    result = await db.execute(
        select(User)
        .where(User.organization_id == org_id)
        .order_by(User.created_at)
        .limit(1)
    )
    owner = result.scalar_one_or_none()
    customer_email = owner.email if owner else ""

    customer = stripe.Customer.create(
        email=customer_email,
        name=org.name,
        metadata={"org_id": str(org_id)},
    )

    if existing is None:
        db.add(OrgSubscription(
            organization_id=org_id,
            stripe_customer_id=customer.id,
            plan="free",
            status="trialing",
        ))
    else:
        existing.stripe_customer_id = customer.id

    await db.commit()
    return customer.id
