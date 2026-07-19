from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import LedgerEntry, LedgerEntryType


def get_balance(db: Session, user_id: str) -> Decimal:
    """
    A user's withdrawable balance is the sum of every ledger entry they own —
    never a stored/cached field. Summed in Python (not SQL SUM) so we stay on
    Decimal arithmetic and never touch SQLite's float aggregate path.
    """
    amounts = db.scalars(
        select(LedgerEntry.amount).where(LedgerEntry.user_id == user_id)
    ).all()
    return sum((Decimal(str(a)) for a in amounts), Decimal("0.00"))


def try_add_entry(
    db: Session,
    *,
    user_id: str,
    type_: LedgerEntryType,
    amount: Decimal,
    sale_id: str | None = None,
    withdrawal_id: str | None = None,
) -> LedgerEntry | None:
    """
    Insert a ledger entry. Returns None instead of raising when an entry of
    this type already exists for the given sale/withdrawal — the caller
    treats that as "already processed", which is what makes the advance
    payout job and webhook handlers safe to run/retry more than once.
    """
    entry = LedgerEntry(
        user_id=user_id,
        sale_id=sale_id,
        withdrawal_id=withdrawal_id,
        type=type_,
        amount=amount,
    )
    try:
        with db.begin_nested():
            db.add(entry)
            db.flush()
    except IntegrityError:
        return None
    return entry
