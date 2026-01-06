"""Custom exceptions for Fabric Demo Automation."""


class FabricAPIError(Exception):
    """Fabric API error with details."""

    def __init__(
        self, message: str, status_code: int | None = None, response: dict | None = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class DemoValidationError(Exception):
    """Error validating demo package structure."""

    pass


class SetupError(Exception):
    """Error during demo setup."""

    pass
