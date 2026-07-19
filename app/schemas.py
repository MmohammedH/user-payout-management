from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    id: str
    name: str


class UserOut(BaseModel):
    id: str
    name: str
    model_config = ConfigDict(from_attributes=True)


class SaleCreate(BaseModel):
    user_id: str = Field(alias="userId")
    brand: str
    earning: Decimal
    model_config = ConfigDict(populate_by_name=True)


class SaleOut(BaseModel):
    id: str
    user_id: str = Field(alias="userId")
    brand: str
    status: str
    earning: Decimal
    created_at: datetime = Field(alias="createdAt")
    reconciled_at: datetime | None = Field(default=None, alias="reconciledAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ReconcileRequest(BaseModel):
    decision: Literal["approved", "rejected"]


class WithdrawalRequest(BaseModel):
    amount: Decimal


class WithdrawalOut(BaseModel):
    id: str
    user_id: str = Field(alias="userId")
    amount: Decimal
    status: str
    created_at: datetime = Field(alias="createdAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WithdrawalWebhookRequest(BaseModel):
    withdrawal_id: str = Field(alias="withdrawalId")
    status: Literal["completed", "cancelled", "rejected", "failed"]
    model_config = ConfigDict(populate_by_name=True)


class BalanceOut(BaseModel):
    user_id: str = Field(alias="userId")
    balance: Decimal
    model_config = ConfigDict(populate_by_name=True)


class LedgerEntryOut(BaseModel):
    id: str
    type: str
    amount: Decimal
    sale_id: str | None = Field(default=None, alias="saleId")
    withdrawal_id: str | None = Field(default=None, alias="withdrawalId")
    created_at: datetime = Field(alias="createdAt")
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AdvancePayoutJobResult(BaseModel):
    paid_sale_ids: list[str] = Field(alias="paidSaleIds")
    skipped_sale_ids: list[str] = Field(alias="skippedSaleIds")
    model_config = ConfigDict(populate_by_name=True)
