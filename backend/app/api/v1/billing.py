"""
Billing endpoints for AgentStudio.

All endpoints require authentication except:
  GET  /billing/plans    — public plan catalogue
  POST /billing/webhook  — Stripe webhook (signature-verified)
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_active_user, block_during_impersonation, require_org_admin
from app.models.user import User
from app.services import billing_service, stripe_webhook_service

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class PortalRequest(BaseModel):
    return_url: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current org's subscription state."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    return await billing_service.get_subscription(current_user.organization_id, db)


@router.post("/checkout")
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: User = Depends(require_org_admin),
    _: None = Depends(block_during_impersonation("Billing actions are not available during impersonation")),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Checkout session for a subscription upgrade."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    try:
        return await billing_service.create_checkout_session(
            current_user.organization_id,
            body.price_id,
            body.success_url,
            body.cancel_url,
            db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/portal")
async def create_portal_session(
    body: PortalRequest,
    current_user: User = Depends(require_org_admin),
    _: None = Depends(block_during_impersonation("Billing actions are not available during impersonation")),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Customer Portal session to manage billing."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    try:
        return await billing_service.create_portal_session(
            current_user.organization_id, body.return_url, db
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/cancel")
async def cancel_subscription(
    current_user: User = Depends(require_org_admin),
    _: None = Depends(block_during_impersonation("Billing actions are not available during impersonation")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel subscription at the end of the current billing period."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    try:
        return await billing_service.cancel_subscription(current_user.organization_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/reactivate")
async def reactivate_subscription(
    current_user: User = Depends(require_org_admin),
    _: None = Depends(block_during_impersonation("Billing actions are not available during impersonation")),
    db: AsyncSession = Depends(get_db),
):
    """Undo a pending cancellation."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    try:
        return await billing_service.reactivate_subscription(current_user.organization_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/invoices")
async def get_invoices(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List past invoices from Stripe."""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User has no organisation")
    return await billing_service.get_invoices(
        current_user.organization_id, max(1, min(limit, 100)), db
    )


@router.get("/plans")
async def get_plans():
    """Public plan catalogue with Stripe price IDs and feature flags."""
    return billing_service.get_plan_catalogue()


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Stripe webhook — signature verified, idempotent."""
    body = await request.body()
    signature = request.headers.get("stripe-signature", "")
    result = await stripe_webhook_service.handle_webhook(body, signature, db)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "webhook_error"))
    return {"received": True}
