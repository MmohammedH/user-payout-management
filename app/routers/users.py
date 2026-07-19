from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import NotFoundError
from app.models import LedgerEntry, User
from app.schemas import BalanceOut, LedgerEntryOut, UserCreate, UserOut
from app.services.ledger_service import get_balance

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.get(User, payload.id)
    if existing is not None:
        return existing
    user = User(id=payload.id, name=payload.name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}/balance", response_model=BalanceOut)
def get_user_balance(user_id: str, db: Session = Depends(get_db)):
    if db.get(User, user_id) is None:
        raise NotFoundError(f"User {user_id} not found")
    return BalanceOut(user_id=user_id, balance=get_balance(db, user_id))


@router.get("/{user_id}/ledger", response_model=list[LedgerEntryOut])
def get_user_ledger(user_id: str, db: Session = Depends(get_db)):
    if db.get(User, user_id) is None:
        raise NotFoundError(f"User {user_id} not found")
    entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.user_id == user_id)
        .order_by(LedgerEntry.created_at)
        .all()
    )
    return entries
