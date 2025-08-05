# 🔐 Authentication Module Documentation

## 📌 Purpose

The authentication module provides flexible AWS credential management for the AI Crawling Strategist package. It supports multiple credential configuration methods with a clear priority hierarchy, ensuring users can easily configure AWS access for Claude Sonnet 3.5 integration while maintaining security best practices.

---

## 🎯 Core Objectives

- **Flexible Configuration**: Support multiple AWS credential sources (profiles, environment variables, direct parameters)
- **Priority-Based Resolution**: Clear hierarchy for credential resolution when multiple sources are available
- **Security-First**: Avoid storing credentials in code, prefer AWS profiles and environment variables
- **Developer Experience**: Simple configuration with helpful error messages
- **Validation**: Optional credential testing to catch configuration issues early

---

## 🏗️ Architecture Overview

### Module Structure

```
auth/
├── __init__.py               # Public exports
├── credentials.py            # Core credential resolution logic
└── profile_manager.py        # AWS profile handling utilities
```

### Key Components

| Component | Purpose |
|-----------|---------|
| **CredentialResolver** | Main class that implements priority-based credential resolution |
| **ProfileManager** | Handles AWS profile discovery and validation |
| **ConfigurationValidator** | Tests credential validity and region compatibility |

---

## 🔄 Credential Resolution Strategy

### Priority Hierarchy (Highest to Lowest)

1. **Direct Parameters** (Override all other sources)
   ```python
   strategist = DOMStrategist(
       aws_access_key_id="AKIA...",
       aws_secret_access_key="...",
       aws_region="us-east-1"
   )
   ```

2. **AWS Profile** (Specified or default)
   ```python
   strategist = DOMStrategist(aws_profile="production")
   # or
   strategist = DOMStrategist()  # Uses 'default' profile
   ```

3. **Global Package Configuration**
   ```python
   import ai_crawling_strategist as acs
   acs.aws_access_key_id = "AKIA..."
   acs.aws_secret_access_key = "..."
   acs.aws_region = "us-east-1"
   ```

4. **Environment Variables** (System level)
   ```bash
   export AWS_ACCESS_KEY_ID="AKIA..."
   export AWS_SECRET_ACCESS_KEY="..."
   export AWS_DEFAULT_REGION="us-east-1"
   ```

### Resolution Algorithm

```python
def resolve_credentials(
    aws_profile=None,
    aws_access_key_id=None,
    aws_secret_access_key=None,
    aws_region=None
):
    """
    Step-by-step credential resolution:
    
    1. If direct parameters provided → use them
    2. If aws_profile specified → load from ~/.aws/credentials
    3. If global config set → use package-level settings
    4. Try default AWS profile → ~/.aws/credentials [default]
    5. Try environment variables → AWS_ACCESS_KEY_ID, etc.
    6. Raise ConfigurationError with helpful guidance
    """
```

---

## 📋 Implementation Details

### credentials.py

**Core Classes:**

```python
class CredentialResolver:
    """Main credential resolution engine"""
    
    def __init__(self):
        self.profile_manager = ProfileManager()
        self.validator = ConfigurationValidator()
    
    def resolve(self, **kwargs) -> AWSCredentials:
        """Implements priority hierarchy and returns validated credentials"""
    
    def test_connection(self, credentials: AWSCredentials) -> bool:
        """Optional validation of credentials against AWS Bedrock"""

class AWSCredentials(BaseModel):
    """Validated credential container"""
    access_key_id: str
    secret_access_key: str
    region: str = "us-east-1"
    session_token: Optional[str] = None  # For temporary credentials

class GlobalConfig:
    """Package-level configuration storage"""
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: Optional[str] = None
```

### profile_manager.py

**AWS Profile Management:**

```python
class ProfileManager:
    """Handles AWS credential file operations"""
    
    def get_profile_credentials(self, profile_name: str) -> Dict[str, str]:
        """Load credentials from ~/.aws/credentials"""
    
    def list_available_profiles(self) -> List[str]:
        """Return all available AWS profiles"""
    
    def validate_profile_exists(self, profile_name: str) -> bool:
        """Check if specified profile exists"""
    
    def get_default_profile(self) -> Optional[Dict[str, str]]:
        """Load default profile if available"""
```

**File Parsing Logic:**
- Parse `~/.aws/credentials` using `configparser`
- Support both `[default]` and named profiles
- Handle credential file format variations
- Graceful handling of missing files

---

## ⚠️ Error Handling Strategy

### Exception Types

```python
class ConfigurationError(Exception):
    """Base class for configuration-related errors"""

class MissingCredentialsError(ConfigurationError):
    """No valid credentials found in any source"""

class InvalidProfileError(ConfigurationError):
    """Specified AWS profile not found"""

class InvalidRegionError(ConfigurationError):
    """Region doesn't support Claude Sonnet 3.5"""

class CredentialValidationError(ConfigurationError):
    """Credentials invalid or insufficient permissions"""
```

### Error Messages

**Missing Credentials:**
```
ConfigurationError: No AWS credentials found.

Please configure credentials using one of these methods:

1. AWS Profile (recommended):
   aws configure --profile your-profile
   
2. Environment variables:
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   
3. Direct parameters:
   DOMStrategist(aws_access_key_id="...", aws_secret_access_key="...")

For more help: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html
```

**Invalid Profile:**
```
InvalidProfileError: AWS profile 'production' not found.

Available profiles: ['default', 'dev', 'staging']

Run 'aws configure --profile production' to create this profile.
```

**Invalid Region:**
```
InvalidRegionError: Region 'eu-central-1' doesn't support Claude Sonnet 3.5.

Supported regions: ['us-east-1', 'us-west-2', 'eu-west-1']
```

---

## 🔧 Integration Points

### Core Module Integration

```python
# strategist.py
from ..auth import CredentialResolver
from ..exceptions import ConfigurationError

class DOMStrategist:
    def __init__(self, aws_profile=None, **auth_params):
        resolver = CredentialResolver()
        try:
            self.credentials = resolver.resolve(
                aws_profile=aws_profile,
                **auth_params
            )
        except ConfigurationError as e:
            # Re-raise with context about the strategist
            raise ConfigurationError(f"Authentication failed: {e}")
```

### Claude Client Integration

```python
# llm/claude_client.py
class ClaudeClient:
    def __init__(self, credentials: AWSCredentials):
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=credentials.access_key_id,
            aws_secret_access_key=credentials.secret_access_key,
            region_name=credentials.region,
            aws_session_token=credentials.session_token
        )
```

## 🚀 Usage Examples

### Basic Usage (AWS Profile)

```python
from ai_crawling_strategist import DOMStrategist

# Uses default AWS profile
strategist = DOMStrategist()

# Uses specific profile
strategist = DOMStrategist(aws_profile="production")
```

### Environment Variables

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"
```

```python
# Automatically picks up environment variables
strategist = DOMStrategist()
```

### Global Configuration

```python
import ai_crawling_strategist as acs

acs.aws_access_key_id = "AKIA..."
acs.aws_secret_access_key = "..."
acs.aws_region = "us-east-1"

strategist = DOMStrategist()  # Uses global config
```

### Direct Parameters

```python
strategist = DOMStrategist(
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    aws_region="us-west-2"
)
```

---

## 📚 Dependencies

### Required Dependencies
```toml
boto3 = "^1.34.0"        # AWS SDK for Python
configparser = "*"       # AWS credential file parsing (built-in)
pydantic = "^2.0.0"      # Data validation
```

### Optional Dependencies
```toml
keyring = "^24.0.0"      # Secure credential storage (future)
```

---