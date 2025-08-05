"""AI Crawling Strategist - DOM parsing with rolling memory."""

from .config import global_config
from .auth import CredentialResolver, AWSCredentials
from .exceptions import ConfigurationError

# Module-level attribute access for global configuration
# Usage: import ai_crawling_strategist as acs; acs.aws_access_key_id = "..."
def __getattr__(name):
    """Handle dynamic attribute access for global configuration."""
    if hasattr(global_config, name):
        return getattr(global_config, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

# Initialize module attributes to support direct assignment
import sys
_this_module = sys.modules[__name__]
_this_module.aws_access_key_id = None
_this_module.aws_secret_access_key = None
_this_module.aws_region = None

# Monkey patch module to sync with global_config
_original_setattr = _this_module.__setattr__

def _patched_setattr(name, value):
    """Sync module attributes with global config."""
    if hasattr(global_config, name):
        setattr(global_config, name, value)
    _original_setattr(name, value)

_this_module.__setattr__ = _patched_setattr

__all__ = [
    "CredentialResolver", 
    "AWSCredentials",
    "ConfigurationError"
]
