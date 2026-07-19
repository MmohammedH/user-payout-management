from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SaleStatus
from app.schemas import ReconcileRequest, SaleOut
from app.services.reconciliation_service import reconcile_sale

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sales/{sale_id}/reconcile", response_model=SaleOut)
def reconcile(sale_id: str, payload: ReconcileRequest, db: Session = Depends(get_db)):
    decision = SaleStatus(payload.decision)
    return reconcile_sale(db, sale_id, decision)
