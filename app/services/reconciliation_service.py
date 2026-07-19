from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import InvalidDecisionError, NotFoundError, SaleAlreadyReconciledError
from app.models import LedgerEntry, LedgerEntryType, Sale, SaleStatus, _utcnow
from app.services.ledger_service import try_add_entry

DECISION_TO_LEDGER_TYPE = {
    SaleStatus.APPROVED: LedgerEntryType.FINAL_PAYOUT,
    SaleStatus.REJECTED: LedgerEntryType.ADJUSTMENT,
}


def reconcile_sale(db: Session, sale_id: str, decision: SaleStatus) -> Sale:
    """
    Applies an admin reconciliation decision to a pending sale.

    Approved: pays out (earning - advance already paid).
    Rejected: claws back whatever advance was already paid (a negative entry).

    Reconciling a sale that isn't pending anymore is refused (409), not
    reprocessed — the ledger entry inserted here is also guarded by the same
    (sale_id, type) unique constraint the advance-payout job relies on, so a
    retried request can never double-apply the adjustment.
    """
    if decision not in DECISION_TO_LEDGER_TYPE:
        raise InvalidDecisionError(f"Decision must be one of {list(DECISION_TO_LEDGER_TYPE)}")

    sale = db.get(Sale, sale_id)
    if sale is None:
        raise NotFoundError(f"Sale {sale_id} not found")
    if sale.status != SaleStatus.PENDING:
        raise SaleAlreadyReconciledError(
            f"Sale {sale_id} was already reconciled as '{sale.status}'"
        )

    advance_entry = db.scalar(
        select(LedgerEntry).where(
            LedgerEntry.sale_id == sale_id,
            LedgerEntry.type == LedgerEntryType.ADVANCE_PAYOUT,
        )
    )
    advance_paid = Decimal(str(advance_entry.amount)) if advance_entry else Decimal("0.00")
    earning = Decimal(str(sale.earning))

    if decision == SaleStatus.APPROVED:
        adjustment = earning - advance_paid
    else:
        adjustment = -advance_paid

    try_add_entry(
        db,
        user_id=sale.user_id,
        type_=DECISION_TO_LEDGER_TYPE[decision],
        amount=adjustment,
        sale_id=sale_id,
    )
    sale.status = decision
    sale.reconciled_at = _utcnow()
    db.commit()
    db.refresh(sale)
    return sale
