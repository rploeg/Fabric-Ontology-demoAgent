"""
Custom exception classes for demo automation.
"""

from typing import Optional, Dict, Any


class DemoAutomationError(Exception):
    """Base exception for demo automation errors."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        msg = self.message
        if self.details:
            msg += f" | Details: {self.details}"
        if self.cause:
            msg += f" | Caused by: {self.cause}"
        return msg


class ConfigurationError(DemoAutomationError):
    """Raised when configuration is invalid or missing."""

    pass


class ValidationError(DemoAutomationError):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        errors: Optional[list] = None,
        warnings: Optional[list] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.errors = errors or []
        self.warnings = warnings or []


class FabricAPIError(DemoAutomationError):
    """Raised when a Fabric API call fails."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.error_code = error_code
        self.request_id = request_id

    def __str__(self) -> str:
        msg = self.message
        if self.status_code:
            msg += f" | HTTP {self.status_code}"
        if self.error_code:
            msg += f" | Code: {self.error_code}"
        if self.request_id:
            msg += f" | RequestId: {self.request_id}"
        return msg

    @property
    def is_retryable(self) -> bool:
        """Check if the error is likely transient and retryable."""
        if self.status_code in (429, 500, 502, 503, 504):
            return True
        return False


class OneLakeError(DemoAutomationError):
    """Raised when OneLake operations fail."""

    pass


class LROTimeoutError(DemoAutomationError):
    """Raised when a long-running operation times out."""

    def __init__(
        self,
        message: str,
        operation_id: Optional[str] = None,
        elapsed_seconds: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.operation_id = operation_id
        self.elapsed_seconds = elapsed_seconds


class ResourceExistsError(DemoAutomationError):
    """Raised when trying to create a resource that already exists."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_name: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.resource_name = resource_name
        self.resource_id = resource_id


class ResourceNotFoundError(DemoAutomationError):
    """Raised when a required resource is not found."""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.resource_name = resource_name


class AuthenticationError(DemoAutomationError):
    """Raised when authentication fails."""

    pass


class RateLimitError(FabricAPIError):
    """Raised when rate limited by the API."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(message, status_code=429, **kwargs)
        self.retry_after = retry_after

    @property
    def is_retryable(self) -> bool:
        return True


class CancellationRequestedError(DemoAutomationError):
    """Raised when a cancellation is requested."""

    pass
