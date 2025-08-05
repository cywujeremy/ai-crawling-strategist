import yaml
import os
from typing import Dict, Any, List
from pathlib import Path


class PromptTemplateLoader:
    """Loads and manages YAML-based prompt templates."""
    
    def __init__(self, templates_dir: str = None):
        """
        Initialize template loader.
        
        Args:
            templates_dir: Path to templates directory. If None, uses default location.
        """
        if templates_dir is None:
            # Default to templates/ directory relative to this file
            current_dir = Path(__file__).parent
            templates_dir = current_dir / "templates"
        
        self.templates_dir = Path(templates_dir)
        self._templates_cache = {}
    
    def load_template(self, template_name: str) -> Dict[str, Any]:
        """
        Load a template from YAML file.
        
        Args:
            template_name: Name of template file (without .yaml extension)
            
        Returns:
            Dict containing template metadata and content
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            yaml.YAMLError: If template file is invalid YAML
        """
        if template_name in self._templates_cache:
            return self._templates_cache[template_name]
        
        template_path = self.templates_dir / f"{template_name}.yaml"
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = yaml.safe_load(f)
        
        # Cache for future use
        self._templates_cache[template_name] = template_data
        return template_data
    
    def render_template(self, template_name: str, **variables) -> str:
        """
        Render a template with provided variables.
        
        Args:
            template_name: Name of template to render
            **variables: Variables to substitute in template
            
        Returns:
            Rendered template string
            
        Raises:
            KeyError: If required variables are missing
        """
        template_data = self.load_template(template_name)
        template_string = template_data.get("template", "")
        
        # Validate required variables
        required_vars = template_data.get("variables", [])
        missing_vars = [var for var in required_vars if var not in variables]
        
        if missing_vars:
            raise KeyError(f"Missing required variables for template '{template_name}': {missing_vars}")
        
        # Render template with variables
        try:
            return template_string.format(**variables)
        except KeyError as e:
            raise KeyError(f"Template variable not provided: {e}")
    
    def list_templates(self) -> List[str]:
        """
        List all available template names.
        
        Returns:
            List of template names (without .yaml extension)
        """
        if not self.templates_dir.exists():
            return []
        
        templates = []
        for file_path in self.templates_dir.glob("*.yaml"):
            templates.append(file_path.stem)
        
        return sorted(templates)
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        Get metadata about a template.
        
        Args:
            template_name: Name of template
            
        Returns:
            Dict with template name, description, version, and required variables
        """
        template_data = self.load_template(template_name)
        
        return {
            "name": template_data.get("name", template_name),
            "description": template_data.get("description", ""),
            "version": template_data.get("version", "1.0"),
            "variables": template_data.get("variables", [])
        }


# Global template loader instance
_template_loader = None

def get_template_loader(templates_dir: str = None) -> PromptTemplateLoader:
    """
    Get global template loader instance.
    
    Args:
        templates_dir: Path to templates directory (only used on first call)
        
    Returns:
        PromptTemplateLoader instance
    """
    global _template_loader
    if _template_loader is None:
        _template_loader = PromptTemplateLoader(templates_dir)
    return _template_loader


def render_chunk_analysis_prompt(
    chunk_index: int,
    total_chunks: int,
    user_intent: str,
    chunk_start_xpath: str,
    nesting_context: str,
    previous_chunk_end: str,
    discovered_facts: str,
    html_chunk: str
) -> str:
    """
    Render chunk analysis prompt template.
    
    Args:
        chunk_index: Current chunk number (1-based)
        total_chunks: Total number of chunks
        user_intent: Original user query/intent
        chunk_start_xpath: XPath position where chunk starts
        nesting_context: Current DOM nesting context
        previous_chunk_end: HTML where previous chunk ended
        discovered_facts: JSON string of current memory state
        html_chunk: Current HTML chunk content
        
    Returns:
        Rendered prompt string
    """
    loader = get_template_loader()
    return loader.render_template(
        "chunk_analysis",
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        user_intent=user_intent,
        chunk_start_xpath=chunk_start_xpath,
        nesting_context=nesting_context,
        previous_chunk_end=previous_chunk_end,
        discovered_facts=discovered_facts,
        html_chunk=html_chunk
    )


def render_schema_generation_prompt(
    user_intent: str,
    final_memory: str
) -> str:
    """
    Render schema generation prompt template.
    
    Args:
        user_intent: Original user query/intent
        final_memory: JSON string of consolidated memory
        
    Returns:
        Rendered prompt string
    """
    loader = get_template_loader()
    return loader.render_template(
        "schema_generation",
        user_intent=user_intent,
        final_memory=final_memory
    )
