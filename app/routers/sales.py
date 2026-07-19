from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import NotFoundError
from app.models import Sale, User
from app.schemas import SaleCreate, SaleOut

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("", response_model=SaleOut, status_code=201)
def create_sale(payload: SaleCreate, db: Session = Depends(get_db)):
    if db.get(User, payload.user_id) is None:
        raise NotFoundError(f"User {payload.user_id} not found")
    sale = Sale(user_id=payload.user_id, brand=payload.brand, earning=payload.earning)
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


@router.get("", response_model=list[SaleOut])
def list_sales(user_id: str | None = Query(default=None, alias="userId"), db: Session = Depends(get_db)):
    query = db.query(Sale)
    if user_id is not None:
        query = query.filter(Sale.user_id == user_id)
    return query.order_by(Sale.created_at).all()


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(sale_id: str, db: Session = Depends(get_db)):
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise NotFoundError(f"Sale {sale_id} not found")
    return sale
