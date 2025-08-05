"""AWS profile management utilities."""

import configparser
import os
from pathlib import Path
from typing import Dict, List, Optional

from ..exceptions import InvalidProfileError


class ProfileManager:
    """Handles AWS credential file operations."""
    
    def __init__(self):
        self.credentials_path = Path.home() / ".aws" / "credentials"
    
    def get_profile_credentials(self, profile_name: str) -> Dict[str, str]:
        """Load credentials from ~/.aws/credentials."""
        if not self.validate_profile_exists(profile_name):
            available = self.list_available_profiles()
            raise InvalidProfileError(
                f"AWS profile '{profile_name}' not found.\n\n"
                f"Available profiles: {available}\n\n"
                f"Run 'aws configure --profile {profile_name}' to create this profile."
            )
        
        config = self._load_credentials_file()
        profile_data = dict(config[profile_name])
        
        # Map AWS credential file keys to standard format
        return {
            "access_key_id": profile_data.get("aws_access_key_id"),
            "secret_access_key": profile_data.get("aws_secret_access_key"),
            "region": profile_data.get("region"),
            "session_token": profile_data.get("aws_session_token")
        }
    
    def list_available_profiles(self) -> List[str]:
        """Return all available AWS profiles."""
        if not self.credentials_path.exists():
            return []
        
        config = self._load_credentials_file()
        return list(config.sections())
    
    def validate_profile_exists(self, profile_name: str) -> bool:
        """Check if specified profile exists."""
        return profile_name in self.list_available_profiles()
    
    def get_default_profile(self) -> Optional[Dict[str, str]]:
        """Load default profile if available."""
        try:
            return self.get_profile_credentials("default")
        except InvalidProfileError:
            return None
    
    def _load_credentials_file(self) -> configparser.ConfigParser:
        """Load and parse AWS credentials file."""
        if not self.credentials_path.exists():
            raise InvalidProfileError("AWS credentials file not found at ~/.aws/credentials")
        
        config = configparser.ConfigParser()
        config.read(self.credentials_path)
        return config
