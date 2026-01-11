"""
Custom exception classes for demo automation.

This module provides a hierarchy of exceptions that wrap SDK errors and
provide consistent error handling throughout the demo automation tool.

Exception Hierarchy:
    DemoAutomationError (base)
    ├── ConfigurationError
    │   └── MissingConfigError
    ├── ValidationError
    │   └── SchemaValidationError
    ├── FabricAPIError
    │   ├── AuthenticationError
    │   ├── RateLimitError
    │   ├── ResourceNotFoundError
    │   └── ResourceExistsError
    ├── OneLakeError
    ├── LROTimeoutError
    ├── BindingError
    └── CancellationRequestedError

SDK Exception Mapping (Unofficial Fabric Ontology SDK v0.2.0+):
    SDK FabricOntologyError  → DemoAutomationError
    SDK AuthenticationError  → AuthenticationError
    SDK ValidationError      → ValidationError
    SDK ApiError            → FabricAPIError
    SDK ApiError (403)      → AuthenticationError (permission denied)
    SDK ResourceNotFoundError → ResourceNotFoundError
    SDK RateLimitError      → RateLimitError
    SDK ConflictError       → ResourceExistsError
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


# =============================================================================
# SDK Exception Conversion Utilities
# =============================================================================

def wrap_sdk_exception(sdk_exception: Exception) -> DemoAutomationError:
    """
    Convert an SDK exception to the appropriate DemoAutomationError subclass.
    
    This provides consistent error handling when SDK operations fail.
    
    Args:
        sdk_exception: Exception from the Unofficial Fabric Ontology SDK
        
    Returns:
        Appropriate DemoAutomationError subclass
        
    Example:
        >>> from fabric_ontology.exceptions import RateLimitError as SDKRateLimitError
        >>> try:
        ...     client.ontologies.create(...)
        ... except SDKRateLimitError as e:
        ...     raise wrap_sdk_exception(e)
    """
    # Import SDK exceptions here to avoid circular imports
    try:
        from fabric_ontology.exceptions import (
            FabricOntologyError,
            AuthenticationError as SDKAuthenticationError,
            ValidationError as SDKValidationError,
            ApiError,
            ResourceNotFoundError as SDKResourceNotFoundError,
            RateLimitError as SDKRateLimitError,
            ConflictError,
        )
    except ImportError:
        # SDK not installed, return generic error
        return DemoAutomationError(str(sdk_exception), cause=sdk_exception)
    
    # Map SDK exceptions to our hierarchy
    if isinstance(sdk_exception, SDKAuthenticationError):
        return AuthenticationError(
            str(sdk_exception),
            cause=sdk_exception,
        )
    
    elif isinstance(sdk_exception, SDKValidationError):
        return ValidationError(
            str(sdk_exception),
            cause=sdk_exception,
        )
    
    elif isinstance(sdk_exception, SDKResourceNotFoundError):
        return ResourceNotFoundError(
            str(sdk_exception),
            cause=sdk_exception,
        )
    
    elif isinstance(sdk_exception, SDKRateLimitError):
        retry_after = getattr(sdk_exception, 'retry_after', None)
        return RateLimitError(
            str(sdk_exception),
            retry_after=retry_after,
            cause=sdk_exception,
        )
    
    elif isinstance(sdk_exception, ConflictError):
        return ResourceExistsError(
            str(sdk_exception),
            cause=sdk_exception,
        )
    
    elif isinstance(sdk_exception, ApiError):
        status_code = getattr(sdk_exception, 'status_code', None)
        error_code = getattr(sdk_exception, 'error_code', None)
        # Handle 403 Forbidden via ApiError status code
        if status_code == 403:
            return AuthenticationError(
                f"Permission denied: {sdk_exception}",
                cause=sdk_exception,
            )
        return FabricAPIError(
            str(sdk_exception),
            status_code=status_code,
            error_code=error_code,
            cause=sdk_exception,
        )
    
    elif isinstance(sdk_exception, FabricOntologyError):
        return DemoAutomationError(
            str(sdk_exception),
            cause=sdk_exception,
        )
    
    # Unknown exception type
    return DemoAutomationError(
        f"SDK error: {sdk_exception}",
        cause=sdk_exception,
    )
