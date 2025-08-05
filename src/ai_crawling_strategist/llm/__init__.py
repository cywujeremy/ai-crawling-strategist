"""
LLM integration module for AWS Claude Sonnet 3.5.

This module provides structured LLM processing with validation, retry mechanisms,
and YAML-based prompt template management.
"""

from .claude_client import ClaudeClient
from .prompt_templates import (
    PromptTemplateLoader,
    get_template_loader,
    render_chunk_analysis_prompt,
    render_schema_generation_prompt
)
from .response_validator import (
    LLMResponseValidator,
    validate_json_response,
    create_retry_validator
)

__all__ = [
    # Core client
    "ClaudeClient",
    
    # Template management
    "PromptTemplateLoader",
    "get_template_loader",
    "render_chunk_analysis_prompt", 
    "render_schema_generation_prompt",
    
    # Response validation
    "LLMResponseValidator",
    "validate_json_response",
    "create_retry_validator",
]
