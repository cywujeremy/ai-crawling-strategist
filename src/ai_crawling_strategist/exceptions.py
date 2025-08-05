"""Custom exceptions for AI Crawling Strategist."""


class ConfigurationError(Exception):
    """Base class for configuration-related errors."""
    pass


class MissingCredentialsError(ConfigurationError):
    """No valid credentials found in any source."""
    pass


class InvalidProfileError(ConfigurationError):
    """Specified AWS profile not found."""
    pass


class InvalidRegionError(ConfigurationError):
    """Region doesn't support Claude Sonnet 3.5."""
    pass


class CredentialValidationError(ConfigurationError):
    """Credentials invalid or insufficient permissions."""
    pass
