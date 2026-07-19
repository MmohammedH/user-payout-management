from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import NotFoundError
from app.models import User, WithdrawalStatus
from app.schemas import WithdrawalOut, WithdrawalRequest, WithdrawalWebhookRequest
from app.services.withdrawal_service import apply_withdrawal_status, request_withdrawal

router = APIRouter(tags=["withdrawals"])


@router.post("/users/{user_id}/withdrawals", response_model=WithdrawalOut, status_code=201)
def create_withdrawal(user_id: str, payload: WithdrawalRequest, db: Session = Depends(get_db)):
    if db.get(User, user_id) is None:
        raise NotFoundError(f"User {user_id} not found")
    return request_withdrawal(db, user_id, payload.amount)


@router.post("/webhooks/payout-status", response_model=WithdrawalOut)
def payout_status_webhook(payload: WithdrawalWebhookRequest, db: Session = Depends(get_db)):
    """
    Payment provider callback for a withdrawal's outcome (completed, or one
    of cancelled/rejected/failed). Delivering the same event twice is safe —
    apply_withdrawal_status() only ever credits the reversal once.
    """
    return apply_withdrawal_status(db, payload.withdrawal_id, WithdrawalStatus(payload.status))
