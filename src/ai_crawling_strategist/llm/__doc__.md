# LLM Integration Module

## Purpose
This module handles all interactions with AWS Claude Sonnet 3.5 for DOM analysis and extraction schema generation. It provides structured LLM processing with validation and retry mechanisms.

## Core Components

### `claude_client.py`
- AWS Bedrock Claude Sonnet 3.5 integration
- Authentication using AWS credentials from auth module
- Single-shot prompt execution with structured responses
- **Throttling Handling**: Exponential backoff retry logic for rate limits
- **Token Usage Tracking**: Input/output token counts and cost estimation
- **Request Structure**: Anthropic Messages API format with configurable parameters
- **Error Recovery**: Graceful handling of API failures and timeouts

### `prompt_templates.py`
- **Chunk Analysis Template**: Processes HTML chunks with rolling memory
- **Schema Generation Template**: Converts final memory into crawl4ai-compatible extraction schema
- Template variables: user intent, HTML chunks, memory state, DOM context
- Loads templates from YAML files for easy maintenance and modification

### `templates/` Directory
- **YAML Template Files**: Structured prompt templates for maintainability
- **Template Versioning**: Support for different template variations
- **Easy Customization**: Non-developers can modify prompts without code changes

### `response_validator.py`
- Pydantic schema validation for LLM responses
- Automatic retry mechanism (max 3 attempts)
- JSON structure enforcement and error recovery
- Selector validation using BeautifulSoup

## Data Flow

1. **Input**: HTML chunk + rolling memory + user intent
2. **Processing**: Claude analysis via prompt templates
3. **Validation**: Pydantic model validation + selector testing
4. **Output**: Updated memory structure or final extraction schema
5. **Error Handling**: Retry on validation failures, fallback strategies

## Integration Points

- **Memory Management**: Receives/updates memory from `core.memory_manager`
- **Authentication**: Uses AWS credentials from `auth` module
- **Models**: Validates against schemas from `models` module
- **Error Handling**: Raises exceptions defined in `exceptions.py`

## Technical Implementation

### AWS Bedrock Request Format
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 80000,
  "temperature": 1,
  "top_p": 0.999,
  "messages": [
    {
      "role": "user", 
      "content": [{"type": "text", "text": "prompt"}]
    }
  ]
}
```

### Retry Strategy
- **Max Retries**: 5 attempts for throttling errors
- **Exponential Backoff**: 30s → 60s → 120s → 240s → 480s
- **Error Detection**: "Model is getting throttled" pattern matching
- **Cost Tracking**: $3/1M input tokens, $15/1M output tokens

## Key Features

- **Anti-Hallucination**: Evidence-based pattern discovery with confidence scoring
- **Robustness**: Automatic retry and graceful error recovery with exponential backoff
- **Validation**: BeautifulSoup verification of LLM-generated selectors
- **Memory Compression**: Intelligent pruning of irrelevant discoveries
- **Cost Monitoring**: Real-time token usage and cost estimation
- **Rate Limit Handling**: Built-in throttling detection and recovery
