"""Authentication module for AWS credential management."""

from .credentials import CredentialResolver, AWSCredentials, ConfigurationValidator
from .profile_manager import ProfileManager

__all__ = [
    "CredentialResolver",
    "AWSCredentials", 
    "ConfigurationValidator",
    "ProfileManager"
]
