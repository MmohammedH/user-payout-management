from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import AdvancePayoutJobResult
from app.services.payout_service import run_advance_payout_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/advance-payout", response_model=AdvancePayoutJobResult)
def trigger_advance_payout_job(db: Session = Depends(get_db)):
    """
    Simulates the scheduled advance-payout job. In production this would be
    invoked by a cron/scheduler rather than an HTTP call, but the endpoint is
    exposed here so the idempotency guarantee is easy to demonstrate: calling
    it twice in a row pays each pending sale's advance exactly once.
    """
    result = run_advance_payout_job(db)
    return AdvancePayoutJobResult(
        paid_sale_ids=result["paid_sale_ids"],
        skipped_sale_ids=result["skipped_sale_ids"],
    )
