from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.exceptions import (
    InsufficientBalanceError,
    InvalidAmountError,
    InvalidDecisionError,
    NotFoundError,
    SaleAlreadyReconciledError,
    WithdrawalTooSoonError,
)
from app.routers import admin, jobs, sales, users, withdrawals

app = FastAPI(title="User Payout Ledger", version="1.0.0")

# No migrations tool wired up for this assignment — create_all is fine for a
# from-scratch SQLite demo. A real deployment would use Alembic migrations.
Base.metadata.create_all(bind=engine)

app.include_router(users.router)
app.include_router(sales.router)
app.include_router(admin.router)
app.include_router(jobs.router)
app.include_router(withdrawals.router)


@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(SaleAlreadyReconciledError)
async def already_reconciled_handler(request: Request, exc: SaleAlreadyReconciledError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(WithdrawalTooSoonError)
async def withdrawal_too_soon_handler(request: Request, exc: WithdrawalTooSoonError):
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc)},
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


@app.exception_handler(InsufficientBalanceError)
async def insufficient_balance_handler(request: Request, exc: InsufficientBalanceError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(InvalidAmountError)
async def invalid_amount_handler(request: Request, exc: InvalidAmountError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(InvalidDecisionError)
async def invalid_decision_handler(request: Request, exc: InvalidDecisionError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.get("/health")
def health():
    return {"status": "ok"}
