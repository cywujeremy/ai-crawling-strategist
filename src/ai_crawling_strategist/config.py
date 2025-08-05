"""Global configuration for AI Crawling Strategist."""

from typing import Optional


class GlobalConfig:
    """Package-level configuration storage."""
    
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: Optional[str] = None


# Global instance for package-level configuration
global_config = GlobalConfig()
