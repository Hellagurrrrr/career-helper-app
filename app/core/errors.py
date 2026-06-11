from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class APIError(Exception):
    """Application-level error carrying an api-design 12 error code.

    Serialized to the unified envelope:
        { "error": { "code", "message", "details" } }
    """

    def __init__(
        self,
        code: str,
        http_status: int,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.http_status = http_status
        self.message = message
        self.details = details

    def to_response(self) -> JSONResponse:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details is not None:
            payload["details"] = self.details
        return JSONResponse(status_code=self.http_status, content={"error": payload})


# Convenience constructors for the error codes in api-design 12.
def validation_error(message: str, field: str | None = None) -> APIError:
    details = {"field": field} if field else None
    return APIError("VALIDATION_ERROR", 400, message, details)


def unsupported_audio_format(message: str = "Please upload an audio file (MP3, WAV, M4A, or WebM).") -> APIError:
    return APIError("UNSUPPORTED_AUDIO_FORMAT", 400, message)


def speech_not_supported(message: str = "Speech features are not supported in this environment.") -> APIError:
    return APIError("SPEECH_NOT_SUPPORTED", 422, message)


def mock_session_incomplete(message: str = "The mock interview has no valid answers to evaluate.") -> APIError:
    return APIError("MOCK_SESSION_INCOMPLETE", 422, message)


def unauthorized(message: str = "Authentication required.") -> APIError:
    return APIError("UNAUTHORIZED", 401, message)


def wrong_password(message: str = "Incorrect password.") -> APIError:
    return APIError("WRONG_PASSWORD", 401, message)


def forbidden(message: str = "You do not have access to this resource.") -> APIError:
    return APIError("FORBIDDEN", 403, message)


def account_not_found(message: str = "No account found for this email.") -> APIError:
    return APIError("ACCOUNT_NOT_FOUND", 404, message)


def not_found(message: str = "Resource not found.") -> APIError:
    return APIError("NOT_FOUND", 404, message)


def email_taken(message: str = "An account with this email already exists.") -> APIError:
    return APIError("EMAIL_TAKEN", 409, message)


def goal_already_added(message: str = "This goal has already been added.") -> APIError:
    return APIError("GOAL_ALREADY_ADDED", 409, message)


def already_applied(message: str = "You have already applied to this job.") -> APIError:
    return APIError("ALREADY_APPLIED", 409, message)


def meeting_already_pending(message: str = "You already have a pending request for this alumni.") -> APIError:
    return APIError("MEETING_ALREADY_PENDING", 409, message)


def file_too_large(message: str = "File is too large.") -> APIError:
    return APIError("FILE_TOO_LARGE", 413, message)


def not_exclusive_job(message: str = "Referrals are only available for exclusive jobs.") -> APIError:
    return APIError("NOT_EXCLUSIVE_JOB", 422, message)


def rate_limited(message: str = "Too many requests.") -> APIError:
    return APIError("RATE_LIMITED", 429, message)


def internal_error(message: str = "Internal server error.") -> APIError:
    return APIError("INTERNAL_ERROR", 500, message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api_error_handler(_: Request, exc: APIError) -> JSONResponse:
        return exc.to_response()

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = first.get("loc", [])
        field = str(loc[-1]) if loc else None
        message = first.get("msg", "Validation error.")
        err = validation_error(message, field)
        return err.to_response()

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else "INTERNAL_ERROR"
        if exc.status_code == 401:
            code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"
        return APIError(code, exc.status_code, str(exc.detail)).to_response()
