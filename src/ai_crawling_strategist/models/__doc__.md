# Models Module

## Purpose
Define Pydantic data models for type-safe data structures across the DOM analysis pipeline.

## Key Components

### memory.py
Rolling memory data structures for tracking extraction patterns:

- **ChunkMemoryInput**: Input memory state for chunk processing
- **ChunkMemoryOutput**: Updated memory state after chunk analysis
- **DiscoveredFacts**: Pattern discoveries and confidence scores
- **DOMPosition**: Current position tracking in DOM tree

### chunks.py
DOM chunk data structures for incremental processing:

- **DOMChunk**: Individual chunk with HTML content and context
- **ChunkContext**: Parent tag stack and DOM path information
- **ChunkingConfig**: Configuration for chunking strategy

### extraction.py
Final extraction schema models for output generation:

- **ExtractionSchema**: Complete extraction plan for crawl4ai with strategy explanation
- **FieldSelector**: CSS/XPath selectors with confidence scores
- **FallbackStrategy**: Alternative selectors for robustness

## Implementation Strategy

1. **Pydantic BaseModel**: All models inherit from BaseModel for validation
2. **Type Safety**: Strict typing with Optional fields where appropriate
3. **Validation Rules**: Field constraints and custom validators
4. **JSON Schema**: Auto-generated schemas for LLM prompt integration
5. **Documentation**: Field descriptions for clear API usage

## Output
Type-safe data structures ensuring consistent interfaces between core modules.
