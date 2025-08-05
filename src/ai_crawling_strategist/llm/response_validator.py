import json
from typing import Dict, Any, Optional, Callable, TypeVar, Type
from pydantic import BaseModel, ValidationError


T = TypeVar('T', bound=BaseModel)


class LLMResponseValidator:
    """Validates and retries LLM responses with Pydantic models."""
    
    def __init__(self, max_retries: int = 3):
        """
        Initialize response validator.
        
        Args:
            max_retries: Maximum number of validation retries
        """
        self.max_retries = max_retries
    
    def validate_and_retry(
        self,
        llm_call: Callable[[], str],
        model_class: Type[T],
        retry_prompt_modifier: Optional[Callable[[str, str], str]] = None
    ) -> Optional[T]:
        """
        Validate LLM response and retry on validation errors.
        
        Args:
            llm_call: Function that calls LLM and returns response string
            model_class: Pydantic model class for validation
            retry_prompt_modifier: Optional function to modify prompt on retry
            
        Returns:
            Validated Pydantic model instance or None if all retries failed
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Get LLM response
                response_text = llm_call()
                
                if response_text is None:
                    continue
                
                # Parse and validate JSON response
                response_data = self._parse_json_response(response_text)
                if response_data is None:
                    continue
                
                # Validate with Pydantic model
                validated_response = model_class.model_validate(response_data)
                return validated_response
                
            except ValidationError as e:
                last_error = f"Validation error: {e}"
                print(f"WARNING: Validation failed on attempt {attempt + 1}/{self.max_retries}: {e}")
                
                # If we have a retry modifier and more attempts, modify the prompt
                if retry_prompt_modifier and attempt < self.max_retries - 1:
                    # This would require modifying the llm_call to accept error feedback
                    # For now, just continue with same prompt
                    pass
                    
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                print(f"ERROR: Unexpected error on attempt {attempt + 1}/{self.max_retries}: {e}")
        
        print(f"ERROR: All {self.max_retries} validation attempts failed. Last error: {last_error}")
        return None
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM response, handling common formatting issues.
        
        Args:
            response_text: Raw LLM response
            
        Returns:
            Parsed JSON dict or None if parsing failed
        """
        if not response_text or not response_text.strip():
            return None
        
        # Clean response text
        cleaned_text = response_text.strip()
        
        # Remove common markdown code block markers
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        
        cleaned_text = cleaned_text.strip()
        
        # Try to parse JSON
        try:
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            print(f"WARNING: JSON parsing failed: {e}")
            print(f"Response text: {cleaned_text[:200]}...")
            return None
    
    def validate_response(
        self,
        response_text: str,
        model_class: Type[T]
    ) -> Optional[T]:
        """
        Validate a single response without retry logic.
        
        Args:
            response_text: LLM response text
            model_class: Pydantic model class for validation
            
        Returns:
            Validated model instance or None if validation failed
        """
        try:
            response_data = self._parse_json_response(response_text)
            if response_data is None:
                return None
            
            return model_class.model_validate(response_data)
            
        except ValidationError as e:
            print(f"Validation error: {e}")
            return None
        except Exception as e:
            print(f"Unexpected validation error: {e}")
            return None


def validate_json_response(response_text: str, model_class: Type[T]) -> Optional[T]:
    """
    Simple function to validate a JSON response against a Pydantic model.
    
    Args:
        response_text: Raw LLM response
        model_class: Pydantic model class for validation
        
    Returns:
        Validated model instance or None if validation failed
    """
    validator = LLMResponseValidator()
    return validator.validate_response(response_text, model_class)


def create_retry_validator(max_retries: int = 3) -> LLMResponseValidator:
    """
    Create a response validator with specified retry count.
    
    Args:
        max_retries: Maximum number of validation retries
        
    Returns:
        LLMResponseValidator instance
    """
    return LLMResponseValidator(max_retries=max_retries)
