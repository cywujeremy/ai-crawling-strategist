"""Final extraction schema models for output generation."""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class SelectorType(str, Enum):
    """Type of CSS/XPath selector."""
    
    CSS = "css"
    XPATH = "xpath"
    COMBINED = "combined"


class FieldSelector(BaseModel):
    """CSS/XPath selectors with confidence scores."""
    
    primary_selector: str = Field(..., description="Main selector for extracting field")
    selector_type: SelectorType = Field(default=SelectorType.CSS, description="Type of selector")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score for this selector")
    fallback_selectors: List[str] = Field(default_factory=list, description="Alternative selectors if primary fails")
    field_description: str = Field(default="", description="Human-readable description of field")
    extraction_method: str = Field(default="text", description="Method to extract value (text, attribute, html)")
    attribute_name: Optional[str] = Field(default=None, description="Attribute name if extraction_method is 'attribute'")
    post_processing: List[str] = Field(default_factory=list, description="Post-processing steps (strip, lower, etc.)")
    
    @validator('primary_selector')
    def selector_must_not_be_empty(cls, v):
        """Ensure selector is not empty"""
        if not v.strip():
            raise ValueError('Primary selector cannot be empty')
        return v
    
    @validator('extraction_method')
    def extraction_method_must_be_valid(cls, v):
        """Ensure extraction method is valid"""
        valid_methods = {'text', 'attribute', 'html', 'href', 'src'}
        if v not in valid_methods:
            raise ValueError(f'Extraction method must be one of: {valid_methods}')
        return v
    
    @validator('attribute_name')
    def attribute_required_for_attribute_extraction(cls, v, values):
        """Ensure attribute name is provided when extraction method is 'attribute'"""
        if values.get('extraction_method') == 'attribute' and not v:
            raise ValueError('Attribute name is required when extraction method is "attribute"')
        return v
    
    def get_crawl4ai_config(self) -> Dict[str, Any]:
        """Convert to crawl4ai-compatible field configuration."""
        config = {
            'selector': self.primary_selector,
            'type': self.selector_type.value
        }
        
        if self.extraction_method == 'attribute' and self.attribute_name:
            config['attribute'] = self.attribute_name
        elif self.extraction_method == 'html':
            config['extract_html'] = True
        
        if self.fallback_selectors:
            config['fallback_selectors'] = self.fallback_selectors
        
        return config


class ContainerSelector(BaseModel):
    """Selector for the main container holding items to extract."""
    
    selector: str = Field(..., description="CSS/XPath selector for container")
    selector_type: SelectorType = Field(default=SelectorType.CSS, description="Type of selector")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in container identification")
    description: str = Field(default="", description="Description of what this container represents")
    expected_item_count: Optional[int] = Field(default=None, ge=0, description="Expected number of items in container")
    
    @validator('selector')
    def selector_must_not_be_empty(cls, v):
        """Ensure selector is not empty"""
        if not v.strip():
            raise ValueError('Container selector cannot be empty')
        return v


class ItemSelector(BaseModel):
    """Selector for individual items within the container."""
    
    selector: str = Field(..., description="CSS/XPath selector for individual items")
    selector_type: SelectorType = Field(default=SelectorType.CSS, description="Type of selector")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in item identification")
    description: str = Field(default="", description="Description of what constitutes an item")
    relative_to_container: bool = Field(default=True, description="Whether selector is relative to container")
    
    @validator('selector')
    def selector_must_not_be_empty(cls, v):
        """Ensure selector is not empty"""
        if not v.strip():
            raise ValueError('Item selector cannot be empty')
        return v


class FallbackStrategy(BaseModel):
    """Alternative selectors for robustness."""
    
    strategy_name: str = Field(..., description="Name of fallback strategy")
    container_selector: Optional[str] = Field(default=None, description="Alternative container selector")
    item_selector: Optional[str] = Field(default=None, description="Alternative item selector")
    field_selectors: Dict[str, str] = Field(default_factory=dict, description="Alternative field selectors")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in fallback strategy")
    usage_conditions: List[str] = Field(default_factory=list, description="Conditions when to use this fallback")
    
    def has_complete_fallback(self, required_fields: List[str]) -> bool:
        """Check if fallback provides all required fields."""
        return (self.container_selector is not None and 
                self.item_selector is not None and
                all(field in self.field_selectors for field in required_fields))


class ExtractionSchema(BaseModel):
    """Complete extraction plan for crawl4ai."""
    
    container: ContainerSelector = Field(..., description="Main container selector")
    item: ItemSelector = Field(..., description="Individual item selector")
    fields: Dict[str, FieldSelector] = Field(..., description="Field extraction definitions")
    fallback_strategies: List[FallbackStrategy] = Field(default_factory=list, description="Alternative extraction strategies")
    schema_confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence in extraction schema")
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about extraction")
    
    @validator('fields')
    def fields_must_not_be_empty(cls, v):
        """Ensure at least one field is defined"""
        if not v:
            raise ValueError('At least one field must be defined')
        return v
    
    def get_high_confidence_fields(self, threshold: float = 0.8) -> Dict[str, FieldSelector]:
        """Get fields with confidence above threshold."""
        return {
            name: selector for name, selector in self.fields.items()
            if selector.confidence >= threshold
        }
    
    def get_required_fields(self) -> List[str]:
        """Get list of field names that are required for extraction."""
        return list(self.fields.keys())
    
    def get_best_fallback(self, required_fields: Optional[List[str]] = None) -> Optional[FallbackStrategy]:
        """Get the best fallback strategy for given required fields."""
        if not self.fallback_strategies:
            return None
        
        if required_fields is None:
            required_fields = self.get_required_fields()
        
        # Filter strategies that provide all required fields
        complete_strategies = [
            strategy for strategy in self.fallback_strategies
            if strategy.has_complete_fallback(required_fields)
        ]
        
        if not complete_strategies:
            return None
        
        # Return strategy with highest confidence
        return max(complete_strategies, key=lambda s: s.confidence)
    
    def to_crawl4ai_config(self) -> Dict[str, Any]:
        """Convert extraction schema to crawl4ai configuration format."""
        config = {
            'container_selector': self.container.selector,
            'item_selector': self.item.selector,
            'fields': {}
        }
        
        # Add field configurations
        for field_name, field_selector in self.fields.items():
            config['fields'][field_name] = field_selector.get_crawl4ai_config()
        
        # Add fallback configuration if available
        best_fallback = self.get_best_fallback()
        if best_fallback:
            config['fallback'] = {
                'container_selector': best_fallback.container_selector,
                'item_selector': best_fallback.item_selector,
                'fields': best_fallback.field_selectors
            }
        
        return config
    
    def validate_completeness(self, user_requirements: List[str]) -> List[str]:
        """Validate that schema covers all user requirements."""
        missing_fields = []
        
        for requirement in user_requirements:
            if requirement not in self.fields:
                missing_fields.append(requirement)
        
        return missing_fields


class ExtractionValidation(BaseModel):
    """Validation results for extraction schema."""
    
    schema_valid: bool = Field(default=True, description="Whether schema is structurally valid")
    field_coverage: Dict[str, bool] = Field(default_factory=dict, description="Coverage of required fields")
    confidence_summary: Dict[str, float] = Field(default_factory=dict, description="Confidence scores summary")
    validation_errors: List[str] = Field(default_factory=list, description="List of validation errors")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")
    
    def add_error(self, error: str):
        """Add a validation error."""
        self.validation_errors.append(error)
        self.schema_valid = False
    
    def add_recommendation(self, recommendation: str):
        """Add a recommendation for improvement."""
        self.recommendations.append(recommendation)
    
    def get_overall_confidence(self) -> float:
        """Calculate overall confidence score."""
        if not self.confidence_summary:
            return 0.0
        
        confidences = list(self.confidence_summary.values())
        return sum(confidences) / len(confidences)
    
    def is_production_ready(self, min_confidence: float = 0.8, max_errors: int = 0) -> bool:
        """Check if schema is ready for production use."""
        return (self.schema_valid and
                len(self.validation_errors) <= max_errors and
                self.get_overall_confidence() >= min_confidence)


class ExtractionResult(BaseModel):
    """Result of applying extraction schema to HTML."""
    
    schema: ExtractionSchema = Field(..., description="Schema used for extraction")
    extracted_data: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted data items")
    extraction_success: bool = Field(default=True, description="Whether extraction was successful")
    items_found: int = Field(ge=0, description="Number of items successfully extracted")
    extraction_errors: List[str] = Field(default_factory=list, description="Errors encountered during extraction")
    fallback_used: Optional[str] = Field(default=None, description="Name of fallback strategy used, if any")
    
    def get_extraction_rate(self, expected_items: Optional[int] = None) -> float:
        """Calculate extraction success rate."""
        if expected_items is None or expected_items == 0:
            return 1.0 if self.extraction_success else 0.0
        
        return min(1.0, self.items_found / expected_items)
    
    def get_field_coverage(self) -> Dict[str, float]:
        """Get coverage percentage for each field."""
        if not self.extracted_data:
            return {}
        
        field_coverage = {}
        total_items = len(self.extracted_data)
        
        # Get all possible field names
        all_fields = set()
        for item in self.extracted_data:
            all_fields.update(item.keys())
        
        # Calculate coverage for each field
        for field in all_fields:
            filled_count = sum(1 for item in self.extracted_data if item.get(field))
            field_coverage[field] = filled_count / total_items
        
        return field_coverage
