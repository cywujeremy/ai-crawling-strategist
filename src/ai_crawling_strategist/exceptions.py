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


# Processing exceptions
class ProcessingError(Exception):
    """Base class for core processing errors."""
    pass


class ChunkingError(ProcessingError):
    """DOM chunking failures."""
    pass


class MemoryError(ProcessingError):
    """Memory management failures."""
    pass


class SchemaGenerationError(ProcessingError):
    """Final schema generation failures."""
    pass


# LLM integration exceptions
class LLMError(Exception):
    """Base class for LLM-related errors."""
    pass


class LLMValidationError(LLMError):
    """LLM response validation failures."""
    pass


class LLMConnectionError(LLMError):
    """LLM API connection or authentication failures."""
    pass


class LLMThrottleError(LLMError):
    """LLM API rate limiting errors."""
    pass
