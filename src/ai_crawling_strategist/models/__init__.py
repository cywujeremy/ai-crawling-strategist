"""Data models for DOM analysis and extraction pipeline."""

# Memory models
from .memory import (
    DOMPosition,
    DiscoveredFacts,
    UserIntent,
    ChunkMemoryInput,
    ChunkMemoryOutput,
    MemoryCompressionStrategy,
    MemoryEvolution
)

# Chunk models
from .chunks import (
    ChunkingStrategy,
    ChunkContext,
    ChunkBoundary,
    DOMChunk,
    ChunkingConfig,
    ChunkingResult
)

# Extraction models
from .extraction import (
    SelectorType,
    FieldSelector,
    ContainerSelector,
    ItemSelector,
    FallbackStrategy,
    ExtractionSchema,
    ExtractionValidation,
    ExtractionResult
)

__all__ = [
    # Memory models
    'DOMPosition',
    'DiscoveredFacts',
    'UserIntent',
    'ChunkMemoryInput',
    'ChunkMemoryOutput',
    'MemoryCompressionStrategy',
    'MemoryEvolution',
    
    # Chunk models
    'ChunkingStrategy',
    'ChunkContext',
    'ChunkBoundary',
    'DOMChunk',
    'ChunkingConfig',
    'ChunkingResult',
    
    # Extraction models
    'SelectorType',
    'FieldSelector',
    'ContainerSelector',
    'ItemSelector',
    'FallbackStrategy',
    'ExtractionSchema',
    'ExtractionValidation',
    'ExtractionResult'
]
