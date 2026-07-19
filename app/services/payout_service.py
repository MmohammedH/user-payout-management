from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LedgerEntryType, Sale, SaleStatus
from app.services.ledger_service import try_add_entry

ADVANCE_PAYOUT_RATE = Decimal("0.10")


def run_advance_payout_job(db: Session) -> dict:
    """
    Pays a 10% advance on every pending sale that hasn't received one yet.
    Safe to re-run or run concurrently: the (sale_id, type) unique constraint
    on LedgerEntry turns a repeat pass over an already-advanced sale into a
    no-op rather than a second payout.
    """
    pending_sales = db.scalars(
        select(Sale).where(Sale.status == SaleStatus.PENDING)
    ).all()

    paid_sale_ids: list[str] = []
    skipped_sale_ids: list[str] = []

    for sale in pending_sales:
        amount = (Decimal(str(sale.earning)) * ADVANCE_PAYOUT_RATE).quantize(Decimal("0.01"))
        entry = try_add_entry(
            db,
            user_id=sale.user_id,
            type_=LedgerEntryType.ADVANCE_PAYOUT,
            amount=amount,
            sale_id=sale.id,
        )
        (paid_sale_ids if entry is not None else skipped_sale_ids).append(sale.id)

    db.commit()
    return {"paid_sale_ids": paid_sale_ids, "skipped_sale_ids": skipped_sale_ids}
