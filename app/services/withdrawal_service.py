from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import (
    InsufficientBalanceError,
    InvalidAmountError,
    NotFoundError,
    WithdrawalTooSoonError,
)
from app.models import LedgerEntryType, Withdrawal, WithdrawalStatus, _utcnow
from app.services.ledger_service import get_balance, try_add_entry

WITHDRAWAL_COOLDOWN = timedelta(hours=24)

# Withdrawals in one of these states never actually reached the user, so they
# don't count as "the withdrawal for this 24h window" — see Question 2 in the
# assignment (failed payout recovery should let the user retry immediately).
TERMINAL_FAILURE_STATUSES = (
    WithdrawalStatus.CANCELLED,
    WithdrawalStatus.REJECTED,
    WithdrawalStatus.FAILED,
)


def request_withdrawal(db: Session, user_id: str, amount: Decimal) -> Withdrawal:
    if amount <= 0:
        raise InvalidAmountError("Withdrawal amount must be positive")

    last_withdrawal = db.scalar(
        select(Withdrawal)
        .where(
            Withdrawal.user_id == user_id,
            Withdrawal.status.notin_(TERMINAL_FAILURE_STATUSES),
        )
        .order_by(Withdrawal.created_at.desc())
        .limit(1)
    )
    if last_withdrawal is not None:
        elapsed = _utcnow() - last_withdrawal.created_at
        if elapsed < WITHDRAWAL_COOLDOWN:
            retry_after = int((WITHDRAWAL_COOLDOWN - elapsed).total_seconds())
            raise WithdrawalTooSoonError(retry_after)

    balance = get_balance(db, user_id)
    if amount > balance:
        raise InsufficientBalanceError(
            f"Requested {amount} exceeds withdrawable balance {balance}"
        )

    withdrawal = Withdrawal(user_id=user_id, amount=amount, status=WithdrawalStatus.INITIATED)
    db.add(withdrawal)
    db.flush()  # assign withdrawal.id before the ledger entry references it

    try_add_entry(
        db,
        user_id=user_id,
        type_=LedgerEntryType.WITHDRAWAL,
        amount=-amount,
        withdrawal_id=withdrawal.id,
    )
    db.commit()
    db.refresh(withdrawal)
    return withdrawal


def apply_withdrawal_status(
    db: Session, withdrawal_id: str, new_status: WithdrawalStatus
) -> Withdrawal:
    """
    Handles a payment-provider callback (webhook) reporting a withdrawal's
    outcome. On cancelled/rejected/failed, the debited amount is credited
    back via a new WITHDRAWAL_REVERSAL entry — never by deleting or editing
    the original debit. The (withdrawal_id, type) unique constraint makes a
    duplicate webhook delivery a no-op instead of a double credit.
    """
    withdrawal = db.get(Withdrawal, withdrawal_id)
    if withdrawal is None:
        raise NotFoundError(f"Withdrawal {withdrawal_id} not found")

    if new_status in TERMINAL_FAILURE_STATUSES:
        try_add_entry(
            db,
            user_id=withdrawal.user_id,
            type_=LedgerEntryType.WITHDRAWAL_REVERSAL,
            amount=withdrawal.amount,
            withdrawal_id=withdrawal.id,
        )

    withdrawal.status = new_status
    db.commit()
    db.refresh(withdrawal)
    return withdrawal
