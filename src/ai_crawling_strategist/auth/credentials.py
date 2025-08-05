"""Core credential resolution logic."""

import os
from typing import Optional

import boto3
from pydantic import BaseModel

from ..config import global_config
from ..exceptions import (
    MissingCredentialsError,
    InvalidRegionError,
    CredentialValidationError
)
from .profile_manager import ProfileManager


class AWSCredentials(BaseModel):
    """Validated credential container."""
    
    access_key_id: str
    secret_access_key: str
    region: str = "us-east-1"
    session_token: Optional[str] = None


class ConfigurationValidator:
    """Tests credential validity and region compatibility."""
    
    SUPPORTED_REGIONS = ["us-east-1", "us-west-2", "eu-west-1"]
    
    def validate_region(self, region: str) -> None:
        """Check if region supports Claude Sonnet 3.5."""
        if region not in self.SUPPORTED_REGIONS:
            raise InvalidRegionError(
                f"Region '{region}' doesn't support Claude Sonnet 3.5.\n\n"
                f"Supported regions: {self.SUPPORTED_REGIONS}"
            )
    
    def test_connection(self, credentials: AWSCredentials) -> bool:
        """Optional validation of credentials against AWS Bedrock."""
        try:
            client = boto3.client(
                'bedrock-runtime',
                aws_access_key_id=credentials.access_key_id,
                aws_secret_access_key=credentials.secret_access_key,
                region_name=credentials.region,
                aws_session_token=credentials.session_token
            )
            # Try to list models to validate credentials
            client.list_foundation_models()
            return True
        except Exception as e:
            raise CredentialValidationError(f"Credential validation failed: {e}")


class CredentialResolver:
    """Main credential resolution engine."""
    
    def __init__(self):
        self.profile_manager = ProfileManager()
        self.validator = ConfigurationValidator()
    
    def resolve(
        self,
        aws_profile: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: Optional[str] = None,
        **kwargs
    ) -> AWSCredentials:
        """Implements priority hierarchy and returns validated credentials."""
        
        # 1. Direct parameters (highest priority)
        if aws_access_key_id and aws_secret_access_key:
            region = aws_region or "us-east-1"
            self.validator.validate_region(region)
            return AWSCredentials(
                access_key_id=aws_access_key_id,
                secret_access_key=aws_secret_access_key,
                region=region
            )
        
        # 2. AWS Profile (specified or default)
        profile_creds = self._try_aws_profile(aws_profile)
        if profile_creds:
            return profile_creds
        
        # 3. Global package configuration
        global_creds = self._try_global_config(aws_region)
        if global_creds:
            return global_creds
        
        # 4. Environment variables
        env_creds = self._try_environment_variables(aws_region)
        if env_creds:
            return env_creds
        
        # No credentials found
        self._raise_missing_credentials_error()
    
    def test_connection(self, credentials: AWSCredentials) -> bool:
        """Optional validation of credentials against AWS Bedrock."""
        return self.validator.test_connection(credentials)
    
    def _try_aws_profile(self, profile_name: Optional[str]) -> Optional[AWSCredentials]:
        """Try to load credentials from AWS profile."""
        try:
            # If profile specified, use it; otherwise try default
            if profile_name:
                profile_data = self.profile_manager.get_profile_credentials(profile_name)
            else:
                profile_data = self.profile_manager.get_default_profile()
                if not profile_data:
                    return None
            
            if not profile_data.get("access_key_id") or not profile_data.get("secret_access_key"):
                return None
            
            region = profile_data.get("region") or "us-east-1"
            self.validator.validate_region(region)
            
            return AWSCredentials(
                access_key_id=profile_data["access_key_id"],
                secret_access_key=profile_data["secret_access_key"],
                region=region,
                session_token=profile_data.get("session_token")
            )
        except Exception:
            return None
    
    def _try_global_config(self, aws_region: Optional[str]) -> Optional[AWSCredentials]:
        """Try to load credentials from global package configuration."""
        if not global_config.aws_access_key_id or not global_config.aws_secret_access_key:
            return None
        
        region = aws_region or global_config.aws_region or "us-east-1"
        self.validator.validate_region(region)
        
        return AWSCredentials(
            access_key_id=global_config.aws_access_key_id,
            secret_access_key=global_config.aws_secret_access_key,
            region=region
        )
    
    def _try_environment_variables(self, aws_region: Optional[str]) -> Optional[AWSCredentials]:
        """Try to load credentials from environment variables."""
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        if not access_key or not secret_key:
            return None
        
        region = (
            aws_region or 
            os.getenv("AWS_DEFAULT_REGION") or 
            os.getenv("AWS_REGION") or 
            "us-east-1"
        )
        self.validator.validate_region(region)
        
        return AWSCredentials(
            access_key_id=access_key,
            secret_access_key=secret_key,
            region=region,
            session_token=os.getenv("AWS_SESSION_TOKEN")
        )
    
    def _raise_missing_credentials_error(self) -> None:
        """Raise helpful error when no credentials found."""
        raise MissingCredentialsError(
            "No AWS credentials found.\n\n"
            "Please configure credentials using one of these methods:\n\n"
            "1. AWS Profile (recommended):\n"
            "   aws configure --profile your-profile\n\n"
            "2. Environment variables:\n"
            "   export AWS_ACCESS_KEY_ID=\"your-key\"\n"
            "   export AWS_SECRET_ACCESS_KEY=\"your-secret\"\n\n"
            "3. Direct parameters:\n"
            "   DOMStrategist(aws_access_key_id=\"...\", aws_secret_access_key=\"...\")\n\n"
            "For more help: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html"
        )
