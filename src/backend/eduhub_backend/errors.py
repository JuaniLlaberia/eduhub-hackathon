"""
Error mapping: every non-2xx response is an ErrorResponse with a status chosen from its ErrorCode.
"""
import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from eduhub_shared.errors import ContractError
from eduhub_shared.models import ApiError, ErrorCode, ErrorResponse

logger = logging.getLogger(__name__)

STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.INVALID_REQUEST: 422,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.ACCOUNT_NOT_FOUND: 404,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.SOURCE_UNAVAILABLE: 503,
    ErrorCode.FEATURE_DISABLED: 501,
    ErrorCode.ANALYSIS_FAILED: 500,
    ErrorCode.GENERATION_FAILED: 500,
    ErrorCode.SIMULATION_FAILED: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}
INTERNAL_MESSAGE = "Ocurrió un error inesperado. Probá de nuevo en unos minutos."
INVALID_MESSAGE = "La solicitud tiene datos inválidos."
NOT_FOUND_MESSAGE = "No encontramos lo que buscás."

class HttpError(Exception):
    """
    Raised by routes to answer with a specific ErrorCode and es-AR message.
    """
    def __init__(self, code: ErrorCode, message: str) -> None:
        """
        Store the error code and user-facing message.
        """
        super().__init__(message)
        self.code = code
        self.message = message

def api_error_from(error: Exception) -> ApiError:
    """
    Convert any exception to a user-safe ApiError; unknown exceptions hide their details.
    """
    if isinstance(error, (ContractError, HttpError)):
        return ApiError(code=error.code, message=error.message)
    return ApiError(code=ErrorCode.INTERNAL_ERROR, message=INTERNAL_MESSAGE)

def error_response(error: ApiError) -> JSONResponse:
    """
    Build the JSON response for error with the status of its code.
    """
    body = ErrorResponse(error=error).model_dump(mode="json")
    return JSONResponse(body, status_code=STATUS_BY_CODE[error.code])

async def handle_known(request: Request, error: Exception) -> JSONResponse:
    """
    Answer contract and API errors with their own code and message.
    """
    return error_response(api_error_from(error))

async def handle_validation(request: Request, error: Exception) -> JSONResponse:
    """
    Answer request validation errors with 422 invalid_request.
    """
    return error_response(ApiError(code=ErrorCode.INVALID_REQUEST, message=INVALID_MESSAGE))

async def handle_http(request: Request, error: Exception) -> JSONResponse:
    """
    Answer framework HTTP errors (unknown path, wrong method) as ErrorResponse.
    """
    status = getattr(error, "status_code", 500)
    if status == 404:
        return error_response(ApiError(code=ErrorCode.NOT_FOUND, message=NOT_FOUND_MESSAGE))
    body = ErrorResponse(error=ApiError(code=ErrorCode.INVALID_REQUEST, message=INVALID_MESSAGE))
    return JSONResponse(body.model_dump(mode="json"), status_code=status)

async def handle_unexpected(request: Request, error: Exception) -> JSONResponse:
    """
    Log unexpected errors and answer 500 internal_error without leaking details.
    """
    logger.exception("unhandled error on %s %s", request.method, request.url.path, exc_info=error)
    return error_response(api_error_from(error))

def install_error_handlers(app: FastAPI) -> None:
    """
    Register every exception handler on app.
    """
    app.add_exception_handler(ContractError, handle_known)
    app.add_exception_handler(HttpError, handle_known)
    app.add_exception_handler(RequestValidationError, handle_validation)
    app.add_exception_handler(StarletteHTTPException, handle_http)
    app.add_exception_handler(Exception, handle_unexpected)
