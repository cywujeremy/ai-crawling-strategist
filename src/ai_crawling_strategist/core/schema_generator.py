"""Final schema generation for converting memory patterns into extraction schemas."""

from typing import Dict, List, Optional
import logging
from bs4 import BeautifulSoup

from ..models.memory import ChunkMemoryOutput
from ..models.extraction import (
    ExtractionSchema, FieldSelector, ContainerSelector, 
    ItemSelector, FallbackStrategy, SelectorType
)
from ..llm import ClaudeClient, render_schema_generation_prompt, validate_json_response
from ..exceptions import ConfigurationError, SchemaGenerationError


logger = logging.getLogger(__name__)


class SchemaGenerator:
    """
    Converts final memory state into crawl4ai-compatible extraction schema.
    
    Takes accumulated pattern knowledge and generates robust, 
    production-ready extraction instructions.
    """
    
    def __init__(self, llm_client: ClaudeClient, confidence_threshold: float = 0.8):
        """
        Initialize schema generator with LLM client.
        
        Args:
            llm_client: Claude client for schema generation
            confidence_threshold: Minimum confidence for inclusion
        """
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ConfigurationError("Confidence threshold must be between 0.0 and 1.0")
        
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
    
    def generate_schema(
        self, 
        final_memory: ChunkMemoryOutput, 
        user_query: str,
        source_html: Optional[str] = None
    ) -> ExtractionSchema:
        """
        Convert memory into final extraction schema.
        
        Process:
        1. Filter high-confidence patterns
        2. Generate primary selectors
        3. Create fallback strategies
        4. Generate natural language strategy explanation
        5. Optimize for crawl4ai compatibility
        6. Validate against source HTML
        
        Args:
            final_memory: Consolidated memory from all chunks
            user_query: Original user extraction intent
            source_html: Original HTML for validation (optional)
            
        Returns:
            ExtractionSchema: Complete extraction plan
        """
        try:
            logger.info("Generating final extraction schema")
            
            # Filter high-confidence patterns
            high_confidence_patterns = self._filter_high_confidence_patterns(final_memory)
            
            # Generate schema using LLM
            # Consolidate memory data for template
            memory_data = {
                "discovered_patterns": high_confidence_patterns,
                "page_understanding": final_memory.updated_facts.page_understanding,
                "target_entities": final_memory.user_intent.target_entities,
                "total_patterns": len(final_memory.updated_facts.structural_patterns),
                "confidence_scores": final_memory.updated_facts.confidence_scores
            }
            
            prompt = render_schema_generation_prompt(
                user_intent=user_query,
                final_memory=str(memory_data)
            )
            
            response = self.llm_client.call_claude(
                prompt=prompt,
                max_tokens=6000,
                temperature=0.1
            )
            
            # Parse JSON response
            import json
            try:
                validated_response = json.loads(response)
            except json.JSONDecodeError as e:
                raise SchemaGenerationError(f"Failed to parse LLM response as JSON: {e}")
            
            # Extract schema components
            container_data = validated_response.get("container_selector", {})
            item_data = validated_response.get("item_selector", {})
            field_data = validated_response.get("field_selectors", {})
            explanation = validated_response.get("strategy_explanation", "")
            
            # Build schema components
            container = self._create_container_selector(container_data, high_confidence_patterns)
            item = self._create_item_selector(item_data, high_confidence_patterns)
            fields = self._create_field_selectors(field_data, final_memory.user_intent.target_entities)
            fallbacks = self._create_fallback_selectors(high_confidence_patterns, fields)
            
            # Calculate overall confidence
            schema_confidence = self._calculate_schema_confidence(container, item, fields)
            
            # Create final schema
            schema = ExtractionSchema(
                container=container,
                item=item,
                fields=fields,
                fallback_strategies=fallbacks,
                schema_confidence=schema_confidence,
                extraction_metadata={
                    "total_patterns_discovered": len(final_memory.updated_facts.structural_patterns),
                    "high_confidence_patterns": len(high_confidence_patterns),
                    "chunks_processed": final_memory.chunk_index + 1,
                    "user_context": final_memory.user_intent.context
                },
                strategy_explanation=explanation
            )
            
            # Validate schema if source HTML provided
            if source_html:
                is_valid = self._validate_schema(schema, source_html)
                if not is_valid:
                    logger.warning("Generated schema failed validation against source HTML")
            
            # Optimize for crawl4ai compatibility
            optimized_schema = self._optimize_for_crawl4ai(schema)
            
            logger.info(f"Generated schema with confidence: {schema_confidence:.2f}")
            return optimized_schema
            
        except Exception as e:
            raise SchemaGenerationError(f"Failed to generate schema: {e}")
    
    def _filter_high_confidence_patterns(self, memory: ChunkMemoryOutput) -> Dict[str, float]:
        """Filter patterns above confidence threshold."""
        return {
            pattern: confidence 
            for pattern, confidence in memory.updated_facts.confidence_scores.items()
            if confidence >= self.confidence_threshold
        }
    
    def _create_container_selector(
        self, 
        container_data: Dict, 
        patterns: Dict[str, float]
    ) -> ContainerSelector:
        """Create container selector from LLM response and patterns."""
        
        # Extract from LLM response or find best container pattern
        selector = container_data.get("selector")
        if not selector and patterns:
            # Find most likely container pattern (highest confidence)
            selector = max(patterns.keys(), key=lambda k: patterns[k])
        
        if not selector:
            selector = "body"  # Fallback to body
        
        return ContainerSelector(
            selector=selector,
            selector_type=SelectorType.CSS,
            confidence=container_data.get("confidence", patterns.get(selector, 0.5)),
            description=container_data.get("description", "Main content container"),
            expected_item_count=container_data.get("expected_count")
        )
    
    def _create_item_selector(
        self, 
        item_data: Dict, 
        patterns: Dict[str, float]
    ) -> ItemSelector:
        """Create item selector from LLM response and patterns."""
        
        selector = item_data.get("selector")
        if not selector:
            # Look for repeating element patterns
            common_elements = [".item", ".card", ".post", ".entry", "li", "tr", "article"]
            for element in common_elements:
                if element in patterns:
                    selector = element
                    break
        
        if not selector:
            selector = "div"  # Fallback
        
        return ItemSelector(
            selector=selector,
            selector_type=SelectorType.CSS,
            confidence=item_data.get("confidence", patterns.get(selector, 0.5)),
            description=item_data.get("description", "Individual content item"),
            relative_to_container=True
        )
    
    def _create_field_selectors(
        self, 
        field_data: Dict, 
        target_entities: List[str]
    ) -> Dict[str, FieldSelector]:
        """Create field selectors for target entities."""
        
        fields = {}
        
        for entity in target_entities:
            entity_config = field_data.get(entity, {})
            
            # Default selectors based on entity type
            default_selectors = self._get_default_selectors(entity)
            
            primary_selector = (
                entity_config.get("selector") or 
                default_selectors.get("primary") or 
                f".{entity}"
            )
            
            fields[entity] = FieldSelector(
                primary_selector=primary_selector,
                selector_type=SelectorType.CSS,
                confidence=entity_config.get("confidence", 0.6),
                fallback_selectors=entity_config.get("fallbacks", default_selectors.get("fallbacks", [])),
                field_description=entity_config.get("description", f"Extract {entity} information"),
                extraction_method=self._get_extraction_method(entity),
                attribute_name=self._get_attribute_name(entity)
            )
        
        return fields
    
    def _create_fallback_selectors(
        self, 
        patterns: Dict[str, float],
        primary_fields: Dict[str, FieldSelector]
    ) -> List[FallbackStrategy]:
        """Generate alternative selectors for robustness."""
        
        fallbacks = []
        
        # Create a generic fallback strategy
        if patterns:
            # Use lower confidence patterns as fallbacks
            fallback_patterns = {
                k: v for k, v in patterns.items() 
                if v < self.confidence_threshold and v > 0.4
            }
            
            if fallback_patterns:
                fallback_fields = {}
                for field_name in primary_fields.keys():
                    # Find best fallback pattern for this field
                    field_pattern = self._find_best_fallback_pattern(field_name, fallback_patterns)
                    if field_pattern:
                        fallback_fields[field_name] = field_pattern
                
                if fallback_fields:
                    fallbacks.append(FallbackStrategy(
                        strategy_name="pattern_based_fallback",
                        container_selector="body",
                        item_selector="*",
                        field_selectors=fallback_fields,
                        confidence=max(fallback_patterns.values()) if fallback_patterns else 0.4,
                        usage_conditions=["primary_selectors_fail", "low_item_count"]
                    ))
        
        return fallbacks
    
    def _get_default_selectors(self, entity: str) -> Dict[str, any]:
        """Get default selectors for common entities."""
        defaults = {
            "title": {
                "primary": "h1, h2, h3, .title, .heading",
                "fallbacks": ["title", ".name", ".header"]
            },
            "price": {
                "primary": ".price, .cost, .amount",
                "fallbacks": ["[data-price]", ".value", ".salary"]
            },
            "description": {
                "primary": ".description, .summary, p",
                "fallbacks": [".details", ".content", ".text"]
            },
            "link": {
                "primary": "a[href]",
                "fallbacks": ["[data-url]", "link"]
            },
            "image": {
                "primary": "img[src]",
                "fallbacks": ["[data-image]", ".image"]
            },
            "date": {
                "primary": ".date, time",
                "fallbacks": ["[datetime]", ".timestamp"]
            }
        }
        
        return defaults.get(entity, {"primary": f".{entity}", "fallbacks": []})
    
    def _get_extraction_method(self, entity: str) -> str:
        """Get appropriate extraction method for entity type."""
        method_map = {
            "link": "attribute",
            "image": "attribute", 
            "url": "attribute",
            "href": "attribute"
        }
        return method_map.get(entity, "text")
    
    def _get_attribute_name(self, entity: str) -> Optional[str]:
        """Get attribute name for attribute-based extraction."""
        attr_map = {
            "link": "href",
            "image": "src",
            "url": "href",
            "href": "href"
        }
        return attr_map.get(entity)
    
    def _find_best_fallback_pattern(self, field_name: str, patterns: Dict[str, float]) -> Optional[str]:
        """Find best fallback pattern for a specific field."""
        # Look for patterns that might match the field name
        for pattern in patterns.keys():
            if field_name.lower() in pattern.lower():
                return pattern
        
        # Return highest confidence pattern as fallback
        if patterns:
            return max(patterns.keys(), key=lambda k: patterns[k])
        
        return None
    
    def _calculate_schema_confidence(
        self, 
        container: ContainerSelector,
        item: ItemSelector, 
        fields: Dict[str, FieldSelector]
    ) -> float:
        """Calculate overall schema confidence."""
        
        confidences = [container.confidence, item.confidence]
        confidences.extend([field.confidence for field in fields.values()])
        
        # Weighted average with container and item having higher weight
        container_weight = 0.3
        item_weight = 0.3
        field_weight = 0.4 / len(fields) if fields else 0.4
        
        weighted_sum = (
            container.confidence * container_weight +
            item.confidence * item_weight +
            sum(field.confidence * field_weight for field in fields.values())
        )
        
        return min(1.0, weighted_sum)
    
    def _optimize_for_crawl4ai(self, schema: ExtractionSchema) -> ExtractionSchema:
        """Ensure compatibility with crawl4ai extraction format."""
        # For now, return as-is. Could add crawl4ai-specific optimizations here
        return schema
    
    def _validate_schema(self, schema: ExtractionSchema, html: str) -> bool:
        """Test schema against source HTML for correctness."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Test container selector
            containers = soup.select(schema.container.selector)
            if not containers:
                logger.warning(f"Container selector '{schema.container.selector}' found no elements")
                return False
            
            # Test item selector within first container
            items = containers[0].select(schema.item.selector)
            if not items:
                logger.warning(f"Item selector '{schema.item.selector}' found no elements")
                return False
            
            # Test field selectors on first item
            for field_name, field_selector in schema.fields.items():
                field_elements = items[0].select(field_selector.primary_selector)
                if not field_elements:
                    logger.warning(f"Field selector '{field_selector.primary_selector}' for '{field_name}' found no elements")
            
            return True
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False
