# 🏗️ Implementation Plan

## 📁 Project Structure

### Overview
Design a pip-installable package with clean separation of concerns and intuitive organization.

### Directory Layout

```
ai-crawling-strategist/
├── pyproject.toml                    # Package configuration, dependencies
├── README.md                         # Package overview and quick start
├── LICENSE                           # MIT/Apache license
├── .gitignore                        # Git ignore patterns
│
├── src/
│   └── ai_crawling_strategist/       # Main package directory
│       ├── __init__.py               # Public API exports
│       ├── __version__.py            # Version info
│       ├── config.py                 # Global configuration management
│       │
│       ├── core/                     # Core functionality
│       │   ├── __init__.py
│       │   ├── strategist.py         # Main DOMStrategist class
│       │   ├── chunker.py            # DOM chunking logic
│       │   ├── memory_manager.py     # Rolling memory management
│       │   └── schema_generator.py   # Final extraction schema output
│       │
│       ├── preprocessing/            # HTML preprocessing
│       │   ├── __init__.py
│       │   ├── html_cleaner.py       # Remove irrelevant tags/attributes
│       │   └── dom_parser.py         # BeautifulSoup DOM parsing utilities
│       │
│       ├── llm/                      # LLM integration
│       │   ├── __init__.py
│       │   ├── claude_client.py      # AWS Claude Sonnet 3.5 integration
│       │   ├── prompt_templates.py   # Chunk analysis & schema generation prompts
│       │   └── response_validator.py # Pydantic validation & retry logic
│       │
│       ├── auth/                     # AWS authentication
│       │   ├── __init__.py
│       │   ├── credentials.py        # AWS credential resolution logic
│       │   └── profile_manager.py    # AWS profile handling
│       │
│       ├── models/                   # Data models
│       │   ├── __init__.py
│       │   ├── memory.py             # Memory input/output schemas
│       │   ├── chunks.py             # Chunk data structures
│       │   └── extraction.py         # Final extraction schema models
│       │
│       └── exceptions.py             # Custom exception classes
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                   # Pytest configuration & fixtures
│   │
│   ├── unit/                         # Unit tests
│   │   ├── test_core/
│   │   ├── test_preprocessing/
│   │   ├── test_llm/
│   │   └── test_auth/
│   │
│   ├── integration/                  # Integration tests
│   │   ├── test_end_to_end.py
│   │   └── test_aws_integration.py
│   │
│   └── fixtures/                     # Test data
│       ├── sample_html/
│       ├── expected_outputs/
│       └── mock_responses/
│
├── examples/                         # Usage examples
│   ├── basic_usage.py
│   ├── advanced_configuration.py
│   ├── job_listings_extraction.py
│   └── product_catalog_extraction.py
│
├── docs/                            # Documentation
│   ├── dev-requirements.md          # Current development requirements
│   ├── robustness-enhancements.md   # Future enhancement ideas
│   ├── api-reference.md             # API documentation
│   ├── configuration-guide.md       # AWS setup instructions
│   └── troubleshooting.md           # Common issues & solutions
│
└── scripts/                         # Development utilities
    ├── build_package.py
    ├── run_tests.py
    └── validate_examples.py
```

### Key Design Principles

#### 🎯 **Separation of Concerns**
- **Core**: Business logic isolated from external dependencies
- **LLM**: All Claude integration in dedicated module
- **Auth**: AWS credential handling separate from core functionality
- **Models**: Pydantic schemas centralized for reuse

#### 📦 **Package Structure**
- **Public API**: Clean imports via `__init__.py`
- **Internal Modules**: Implementation details hidden from users
- **Configuration**: Global settings managed centrally
- **Exceptions**: Custom error types for better error handling

#### 🧪 **Testing Strategy**
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test AWS integration and end-to-end flows
- **Fixtures**: Reusable test data and mock responses
- **Examples**: Validation that examples actually work

#### 📚 **Documentation**
- **User-Facing**: API reference and configuration guides
- **Developer-Facing**: Architecture decisions and enhancement plans
- **Examples**: Real-world usage patterns

### Package Entry Points

#### Main API
```python
# Primary user interface
from ai_crawling_strategist import DOMStrategist

# Advanced imports for power users
from ai_crawling_strategist.models import ExtractionSchema
from ai_crawling_strategist.exceptions import ConfigurationError
```

#### Configuration
```python
# Global configuration (similar to OpenAI package)
import ai_crawling_strategist as acs
acs.aws_access_key_id = "your-key"
acs.aws_region = "us-east-1"
```
