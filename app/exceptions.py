class DomainError(Exception):
    """Base class for errors the API layer maps to a specific HTTP status."""


class NotFoundError(DomainError):
    pass


class SaleAlreadyReconciledError(DomainError):
    pass


class WithdrawalTooSoonError(DomainError):
    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Only one withdrawal is allowed every 24 hours. Try again in "
            f"{retry_after_seconds} seconds."
        )


class InsufficientBalanceError(DomainError):
    pass


class InvalidAmountError(DomainError):
    pass


class InvalidDecisionError(DomainError):
    pass
