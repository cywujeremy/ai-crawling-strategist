"""Rolling memory data structures for tracking extraction patterns."""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime


class DOMPosition(BaseModel):
    """Current position tracking in DOM tree."""
    
    xpath: str = Field(..., description="Current XPath location in DOM")
    nesting_context: str = Field(..., description="HTML context of open parent tags")
    previous_chunk_end: str = Field(default="", description="HTML content at end of previous chunk")
    nesting_level: int = Field(ge=0, description="Current depth in DOM tree")
    
    @validator('xpath')
    def xpath_must_be_valid(cls, v):
        """Ensure xpath starts with // or /"""
        if not v.startswith(('/', '//')):
            raise ValueError('XPath must start with / or //')
        return v


class DiscoveredFacts(BaseModel):
    """Pattern discoveries and confidence scores."""
    
    structural_patterns: List[str] = Field(default_factory=list, description="Discovered CSS/XPath patterns")
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Pattern confidence scores (0.0-1.0)")
    page_understanding: str = Field(default="", description="High-level understanding of page structure")
    discarded_hypotheses: List[str] = Field(default_factory=list, description="Patterns that were rejected")
    new_discoveries: List[str] = Field(default_factory=list, description="Patterns found in current chunk")
    
    @validator('confidence_scores')
    def confidence_must_be_valid_range(cls, v):
        """Ensure all confidence scores are between 0.0 and 1.0"""
        for key, score in v.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(f'Confidence score for {key} must be between 0.0 and 1.0, got {score}')
        return v
    
    def add_pattern(self, pattern: str, confidence: float, description: str = ""):
        """Add a new pattern with confidence score."""
        self.structural_patterns.append(pattern)
        self.confidence_scores[pattern] = confidence
        if description:
            self.new_discoveries.append(f"{pattern}: {description}")
    
    def discard_pattern(self, pattern: str, reason: str):
        """Mark a pattern as discarded with reason."""
        if pattern in self.structural_patterns:
            self.structural_patterns.remove(pattern)
        if pattern in self.confidence_scores:
            del self.confidence_scores[pattern]
        self.discarded_hypotheses.append(f"{pattern} ({reason})")


class UserIntent(BaseModel):
    """User's extraction intent and requirements."""
    
    original_query: str = Field(..., description="Original natural language query")
    target_entities: List[str] = Field(..., description="List of data fields to extract")
    context: str = Field(default="", description="Context or domain (e.g., 'job listings', 'products')")
    
    @validator('target_entities')
    def entities_must_not_be_empty(cls, v):
        """Ensure at least one target entity is specified"""
        if not v:
            raise ValueError('At least one target entity must be specified')
        return v


class ChunkMemoryInput(BaseModel):
    """Input memory state for chunk processing."""
    
    chunk_start_position: DOMPosition = Field(..., description="Starting position for current chunk")
    user_intent: UserIntent = Field(..., description="User's extraction requirements")
    discovered_facts: DiscoveredFacts = Field(default_factory=DiscoveredFacts, description="Previously discovered patterns")
    chunk_index: int = Field(ge=0, description="Current chunk number (0-based)")
    total_chunks: int = Field(ge=1, description="Total number of chunks to process")
    
    @validator('chunk_index')
    def chunk_index_must_be_valid(cls, v, values):
        """Ensure chunk index is less than total chunks"""
        if 'total_chunks' in values and v >= values['total_chunks']:
            raise ValueError('Chunk index must be less than total chunks')
        return v


class ChunkMemoryOutput(BaseModel):
    """Updated memory state after chunk analysis."""
    
    chunk_end_position: DOMPosition = Field(..., description="Ending position after processing chunk")
    user_intent: UserIntent = Field(..., description="User intent (should remain unchanged)")
    updated_facts: DiscoveredFacts = Field(..., description="Updated pattern discoveries")
    processing_notes: str = Field(default="", description="Notes about chunk processing")
    chunk_index: int = Field(ge=0, description="Index of processed chunk")
    
    def consolidate_patterns(self, min_confidence: float = 0.5) -> Dict[str, float]:
        """Get consolidated patterns above minimum confidence threshold."""
        return {
            pattern: confidence 
            for pattern, confidence in self.updated_facts.confidence_scores.items()
            if confidence >= min_confidence
        }
    
    def get_high_confidence_patterns(self, threshold: float = 0.8) -> List[str]:
        """Get patterns with confidence above threshold."""
        return [
            pattern for pattern, confidence in self.updated_facts.confidence_scores.items()
            if confidence >= threshold
        ]


class MemoryCompressionStrategy(BaseModel):
    """Strategy for compressing memory to manage token usage."""
    
    max_patterns: int = Field(default=20, ge=1, description="Maximum number of patterns to keep")
    min_confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum confidence to retain pattern")
    prioritize_recent: bool = Field(default=True, description="Whether to prioritize recently discovered patterns")
    keep_user_intent_matches: bool = Field(default=True, description="Always keep patterns matching user intent")
    
    def should_compress(self, facts: DiscoveredFacts) -> bool:
        """Determine if memory compression is needed."""
        return len(facts.structural_patterns) > self.max_patterns
    
    def compress_facts(self, facts: DiscoveredFacts) -> DiscoveredFacts:
        """Apply compression strategy to discovered facts."""
        if not self.should_compress(facts):
            return facts
        
        # Filter by confidence threshold
        high_confidence_patterns = [
            pattern for pattern, confidence in facts.confidence_scores.items()
            if confidence >= self.min_confidence_threshold
        ]
        
        # Sort by confidence (descending)
        sorted_patterns = sorted(
            high_confidence_patterns,
            key=lambda p: facts.confidence_scores[p],
            reverse=True
        )
        
        # Keep top patterns up to max_patterns
        kept_patterns = sorted_patterns[:self.max_patterns]
        
        # Create compressed facts
        compressed_facts = DiscoveredFacts(
            structural_patterns=kept_patterns,
            confidence_scores={p: facts.confidence_scores[p] for p in kept_patterns},
            page_understanding=facts.page_understanding,
            discarded_hypotheses=facts.discarded_hypotheses + [
                f"Compressed out: {p}" for p in facts.structural_patterns 
                if p not in kept_patterns
            ]
        )
        
        return compressed_facts


class MemoryEvolution(BaseModel):
    """Tracks how memory evolves during processing."""
    
    chunk_memories: List[ChunkMemoryOutput] = Field(default_factory=list, description="Memory state after each chunk")
    compression_events: List[str] = Field(default_factory=list, description="Log of compression events")
    pattern_evolution: Dict[str, List[float]] = Field(default_factory=dict, description="Confidence evolution per pattern")
    
    def add_chunk_memory(self, memory: ChunkMemoryOutput):
        """Add memory state from processed chunk."""
        self.chunk_memories.append(memory)
        
        # Track pattern confidence evolution
        for pattern, confidence in memory.updated_facts.confidence_scores.items():
            if pattern not in self.pattern_evolution:
                self.pattern_evolution[pattern] = []
            self.pattern_evolution[pattern].append(confidence)
    
    def get_final_memory(self) -> Optional[ChunkMemoryOutput]:
        """Get the final memory state after all chunks."""
        return self.chunk_memories[-1] if self.chunk_memories else None
    
    def get_stable_patterns(self, min_chunks: int = 3, confidence_threshold: float = 0.8) -> List[str]:
        """Get patterns that remained stable across multiple chunks."""
        stable_patterns = []
        
        for pattern, confidences in self.pattern_evolution.items():
            if (len(confidences) >= min_chunks and 
                all(c >= confidence_threshold for c in confidences[-min_chunks:])):
                stable_patterns.append(pattern)
        
        return stable_patterns
