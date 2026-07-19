import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    # Naive UTC on purpose: SQLite has no real timezone-aware storage, so a
    # mix of aware/naive datetimes here would break the 24h-cooldown math.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SaleStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WithdrawalStatus(str, enum.Enum):
    INITIATED = "initiated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


class LedgerEntryType(str, enum.Enum):
    ADVANCE_PAYOUT = "ADVANCE_PAYOUT"
    FINAL_PAYOUT = "FINAL_PAYOUT"
    ADJUSTMENT = "ADJUSTMENT"
    WITHDRAWAL = "WITHDRAWAL"
    WITHDRAWAL_REVERSAL = "WITHDRAWAL_REVERSAL"


class User(Base):
    """id is the natural userId (e.g. "john_doe") — matches the reference data, no surrogate key needed."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    sales: Mapped[list["Sale"]] = relationship(back_populates="user")
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="user")
    withdrawals: Mapped[list["Withdrawal"]] = relationship(back_populates="user")


class Sale(Base):
    __tablename__ = "sales"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    brand: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[SaleStatus] = mapped_column(
        String, nullable=False, default=SaleStatus.PENDING
    )
    earning: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=_utcnow)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    user: Mapped["User"] = relationship(back_populates="sales")
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="sale")


class Withdrawal(Base):
    __tablename__ = "withdrawals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[WithdrawalStatus] = mapped_column(
        String, nullable=False, default=WithdrawalStatus.INITIATED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="withdrawals")
    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="withdrawal")


class LedgerEntry(Base):
    """
    Append-only. A user's balance is SUM(amount) over their entries — never a
    field that gets mutated in place. The two unique constraints below are what
    make the advance-payout job and reconciliation safe to re-run/retry:
    at most one ADVANCE_PAYOUT / FINAL_PAYOUT / ADJUSTMENT row per sale, and at
    most one WITHDRAWAL / WITHDRAWAL_REVERSAL row per withdrawal.
    """

    __tablename__ = "ledger_entries"
    __table_args__ = (
        UniqueConstraint("sale_id", "type", name="uq_ledger_sale_type"),
        UniqueConstraint("withdrawal_id", "type", name="uq_ledger_withdrawal_type"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    sale_id: Mapped[str | None] = mapped_column(ForeignKey("sales.id"), nullable=True)
    withdrawal_id: Mapped[str | None] = mapped_column(ForeignKey("withdrawals.id"), nullable=True)
    type: Mapped[LedgerEntryType] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="ledger_entries")
    sale: Mapped["Sale | None"] = relationship(back_populates="ledger_entries")
    withdrawal: Mapped["Withdrawal | None"] = relationship(back_populates="ledger_entries")
