"""
Webhook endpoints for Stripe events
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.db.session import get_db
from app.services.webhook_service import WebhookService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Stripe webhook events
    
    This endpoint receives webhook events from Stripe and processes them.
    Events include subscription creation, updates, cancellations, and payment failures.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Dict with processing result
        
    Raises:
        HTTPException: If signature verification fails or processing error occurs
    """
    # Get raw body and signature
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        logger.error("Missing Stripe signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    try:
        # Verify webhook signature
        event = WebhookService.verify_webhook_signature(payload, signature)
        
        # Log event for audit
        logger.info(
            f"Received webhook event: {event['type']} (ID: {event['id']})"
        )
        
        # Process event
        result = await WebhookService.handle_webhook_event(db, event)
        
        return result
        
    except ValueError as e:
        logger.error(f"Invalid webhook signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signature: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )
