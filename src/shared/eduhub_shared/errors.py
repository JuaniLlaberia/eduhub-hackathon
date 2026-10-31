"""
Exceptions raised by interface implementations. The backend maps them to ErrorCode values.
"""
from eduhub_shared.models import ErrorCode

class ContractError(Exception):
    """
    Base class for errors crossing a contract boundary. message must be safe to show to users (es-AR).
    """
    code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(self, message: str) -> None:
        """
        Store the user-facing message.
        """
        super().__init__(message)
        self.message = message

class AccountNotFoundError(ContractError):
    """
    The handle does not exist or is not accessible.
    """
    code = ErrorCode.ACCOUNT_NOT_FOUND

class SourceUnavailableError(ContractError):
    """
    The data source failed (network, auth, provider outage).
    """
    code = ErrorCode.SOURCE_UNAVAILABLE

class RateLimitedError(ContractError):
    """
    The data source or LLM provider rate-limited us.
    """
    code = ErrorCode.RATE_LIMITED

class AnalysisError(ContractError):
    """
    The analyzer could not produce a report (e.g. not enough posts).
    """
    code = ErrorCode.ANALYSIS_FAILED

class GenerationError(ContractError):
    """
    The draft generator failed.
    """
    code = ErrorCode.GENERATION_FAILED

class SimulationError(ContractError):
    """
    The audience simulator failed.
    """
    code = ErrorCode.SIMULATION_FAILED
