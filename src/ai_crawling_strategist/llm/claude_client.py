import json
import time
import boto3
from typing import Tuple, Dict, Any, Optional


class ClaudeClient:
    """AWS Bedrock Claude Sonnet 3.5 client with retry logic and cost tracking."""
    
    def __init__(
        self,
        model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        region_name: str = "us-east-1",
        max_retries: int = 5,
        initial_wait_time: int = 30
    ):
        """
        Initialize Claude client.
        
        Args:
            model_id: Claude model identifier
            region_name: AWS region for Bedrock
            max_retries: Maximum retry attempts for throttling
            initial_wait_time: Initial wait time in seconds for exponential backoff
        """
        self.model_id = model_id
        self.max_retries = max_retries
        self.initial_wait_time = initial_wait_time
        self.client = boto3.client("bedrock-runtime", region_name=region_name)
    
    def invoke(
        self,
        prompt: str,
        max_tokens: int = 80000,
        temperature: float = 1.0,
        top_p: float = 0.999
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Invoke Claude with retry logic for throttling errors.
        
        Args:
            prompt: Input prompt for the model
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            
        Returns:
            Tuple of (response_text, token_usage_dict)
            token_usage_dict contains: input_tokens, output_tokens, total_tokens, estimated_cost
        """
        request_body = self._build_request(prompt, max_tokens, temperature, top_p)
        
        retries = 0
        wait_time = self.initial_wait_time
        
        while retries < self.max_retries:
            try:
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(request_body)
                )
                model_response = json.loads(response["body"].read())
                
                # Extract response text and calculate usage
                response_text = model_response["content"][0]["text"]
                usage_info = self._calculate_usage(model_response.get("usage", {}))
                
                return response_text, usage_info
                
            except Exception as e:
                error_message = str(e)
                
                # Handle throttling errors with exponential backoff
                if "Model is getting throttled" in error_message:
                    retries += 1
                    print(f"WARNING: Model throttled. Retrying in {wait_time}s... (Attempt {retries}/{self.max_retries})")
                    time.sleep(wait_time)
                    wait_time *= 2  # Exponential backoff
                else:
                    print(f"ERROR: Failed to invoke Claude model. Reason: {e}")
                    break
        
        print("ERROR: Max retries reached. Failed to invoke the model.")
        return None, self._empty_usage()
    
    def _build_request(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float
    ) -> Dict[str, Any]:
        """Build Anthropic Messages API request format."""
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "top_k": 250,
            "stop_sequences": [],
            "temperature": temperature,
            "top_p": top_p,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }
    
    def _calculate_usage(self, usage: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate token usage and estimated cost."""
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        # Claude 3.5 Sonnet pricing: $3/1M input, $15/1M output
        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00
        total_cost = input_cost + output_cost
        
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "estimated_cost": total_cost
        }
    
    def _empty_usage(self) -> Dict[str, Any]:
        """Return empty usage info for failed requests."""
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0
        }
