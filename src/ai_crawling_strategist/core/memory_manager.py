"""Rolling memory evolution for tracking extraction patterns across DOM chunks."""

from typing import Dict, List, Optional
import logging
from bs4 import BeautifulSoup

from ..models.memory import (
    ChunkMemoryInput, ChunkMemoryOutput, DiscoveredFacts, 
    UserIntent, DOMPosition, MemoryCompressionStrategy
)
from ..models.chunks import DOMChunk
from ..llm import ClaudeClient, render_chunk_analysis_prompt, validate_json_response
from ..exceptions import ConfigurationError


logger = logging.getLogger(__name__)


class MemoryError(Exception):
    """Memory management failures."""
    pass


class MemoryManager:
    """
    Manages evolution of extraction pattern memory across DOM chunks.
    
    Responsibilities:
    - Initialize memory with user intent
    - Update memory after each chunk analysis
    - Compress memory to prevent token overflow
    - Maintain confidence scores for patterns
    - Discard irrelevant discoveries
    """
    
    def __init__(
        self, 
        llm_client: ClaudeClient,
        compression_threshold: int = 50,
        confidence_threshold: float = 0.8
    ):
        """
        Initialize memory manager with LLM client and compression settings.
        
        Args:
            llm_client: Claude client from llm module
            compression_threshold: Max memory items before compression
            confidence_threshold: Minimum confidence for pattern retention
        """
        if compression_threshold < 10:
            raise ConfigurationError("Compression threshold must be at least 10")
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ConfigurationError("Confidence threshold must be between 0.0 and 1.0")
        
        self.llm_client = llm_client
        self.compression_threshold = compression_threshold
        self.confidence_threshold = confidence_threshold
        self.compression_strategy = MemoryCompressionStrategy(
            max_patterns=compression_threshold,
            min_confidence_threshold=confidence_threshold
        )
    
    def initialize_memory(self, user_query: str) -> ChunkMemoryInput:
        """
        Create initial memory state from user intent.
        
        Args:
            user_query: Natural language extraction goal
            
        Returns:
            ChunkMemoryInput: Initial memory structure
        """
        try:
            # Parse user intent to extract target entities
            target_entities = self._extract_target_entities(user_query)
            
            user_intent = UserIntent(
                original_query=user_query,
                target_entities=target_entities,
                context=self._infer_context(user_query)
            )
            
            # Initialize starting position
            start_position = DOMPosition(
                xpath="//html",
                nesting_context="",
                previous_chunk_end="",
                nesting_level=0
            )
            
            # Create initial memory with empty discoveries
            initial_memory = ChunkMemoryInput(
                chunk_start_position=start_position,
                user_intent=user_intent,
                discovered_facts=DiscoveredFacts(),
                chunk_index=0,
                total_chunks=1  # Will be updated when chunks are available
            )
            
            logger.info(f"Initialized memory for query: {user_query[:100]}...")
            return initial_memory
            
        except Exception as e:
            raise MemoryError(f"Failed to initialize memory: {e}")
    
    def process_chunk(
        self, 
        chunk: DOMChunk, 
        current_memory: ChunkMemoryInput
    ) -> ChunkMemoryOutput:
        """
        Analyze chunk and update memory with new discoveries.
        
        Process:
        1. Prepare LLM prompt with chunk + memory
        2. Call Claude for pattern analysis
        3. Validate response against Pydantic schema
        4. Merge new patterns with existing memory
        5. Update confidence scores
        6. Trigger compression if needed
        
        Args:
            chunk: Current DOM chunk to analyze
            current_memory: Current memory state
            
        Returns:
            ChunkMemoryOutput: Updated memory with new discoveries
        """
        try:
            logger.info(f"Processing chunk {chunk.chunk_index}/{chunk.total_chunks}")
            
            # Prepare prompt for LLM analysis
            prompt = render_chunk_analysis_prompt(
                html_chunk=chunk.html_content,
                user_query=current_memory.user_intent.original_query,
                discovered_patterns=current_memory.discovered_facts.structural_patterns,
                chunk_context=chunk.context.get_context_html(),
                chunk_index=chunk.chunk_index,
                total_chunks=chunk.total_chunks
            )
            
            # Call LLM for chunk analysis
            response = self.llm_client.call_claude(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.1
            )
            
            # Validate and parse response
            validated_response = validate_json_response(response, expected_schema="chunk_analysis")
            
            # Extract new patterns from response
            new_patterns = validated_response.get("discovered_patterns", [])
            pattern_confidences = validated_response.get("confidence_scores", {})
            understanding = validated_response.get("page_understanding", "")
            
            # Validate patterns against actual HTML
            valid_patterns = self._validate_patterns(new_patterns, chunk.html_content)
            
            # Update discovered facts
            updated_facts = self._merge_discoveries(
                current_memory.discovered_facts,
                valid_patterns,
                pattern_confidences,
                understanding
            )
            
            # Update DOM position
            end_position = DOMPosition(
                xpath=f"//html[position()>={chunk.boundary.end_position}]",
                nesting_context=chunk.context.get_context_html(),
                previous_chunk_end=chunk.html_content[-200:] if len(chunk.html_content) > 200 else chunk.html_content,
                nesting_level=chunk.context.nesting_level
            )
            
            # Create output memory
            output_memory = ChunkMemoryOutput(
                chunk_end_position=end_position,
                user_intent=current_memory.user_intent,
                updated_facts=updated_facts,
                processing_notes=f"Processed chunk {chunk.chunk_index}, found {len(valid_patterns)} new patterns",
                chunk_index=chunk.chunk_index
            )
            
            # Apply compression if needed
            if self._needs_compression(updated_facts):
                logger.info("Applying memory compression")
                output_memory.updated_facts = self.compression_strategy.compress_facts(updated_facts)
            
            return output_memory
            
        except Exception as e:
            raise MemoryError(f"Failed to process chunk {chunk.chunk_index}: {e}")
    
    def compress_memory(self, memory: ChunkMemoryOutput) -> ChunkMemoryInput:
        """
        Intelligent memory compression to prevent token overflow.
        
        Strategy:
        1. Consolidate similar patterns
        2. Remove low-confidence discoveries
        3. Prioritize recent findings
        4. Maintain pattern diversity
        5. Preserve high-confidence selectors
        
        Args:
            memory: Current memory state
            
        Returns:
            ChunkMemoryInput: Compressed memory for next chunk
        """
        try:
            # Apply compression strategy
            compressed_facts = self.compression_strategy.compress_facts(memory.updated_facts)
            
            # Create new input memory from compressed state
            compressed_memory = ChunkMemoryInput(
                chunk_start_position=memory.chunk_end_position,
                user_intent=memory.user_intent,
                discovered_facts=compressed_facts,
                chunk_index=memory.chunk_index + 1,
                total_chunks=memory.updated_facts.confidence_scores.get("total_chunks", 1)
            )
            
            logger.info(f"Compressed memory: {len(memory.updated_facts.structural_patterns)} -> {len(compressed_facts.structural_patterns)} patterns")
            return compressed_memory
            
        except Exception as e:
            raise MemoryError(f"Failed to compress memory: {e}")
    
    def _extract_target_entities(self, user_query: str) -> List[str]:
        """Extract target entities from user query."""
        # Simple keyword extraction - could be enhanced with NLP
        entities = []
        
        # Common extraction targets
        entity_keywords = {
            "title": ["title", "name", "heading"],
            "price": ["price", "cost", "amount", "salary"],
            "description": ["description", "summary", "details"],
            "link": ["link", "url", "href"],
            "image": ["image", "photo", "picture"],
            "date": ["date", "time", "when"],
            "author": ["author", "by", "creator"],
            "category": ["category", "type", "genre"],
            "rating": ["rating", "score", "stars"],
            "location": ["location", "address", "where"]
        }
        
        query_lower = user_query.lower()
        for entity, keywords in entity_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                entities.append(entity)
        
        # Fallback: assume generic content extraction
        if not entities:
            entities = ["title", "description", "link"]
        
        return entities
    
    def _infer_context(self, user_query: str) -> str:
        """Infer domain context from user query."""
        context_patterns = {
            "job listings": ["job", "position", "career", "employment"],
            "products": ["product", "item", "buy", "shop", "store"],
            "articles": ["article", "blog", "news", "post"],
            "events": ["event", "meeting", "conference", "show"],
            "people": ["people", "person", "profile", "contact"]
        }
        
        query_lower = user_query.lower()
        for context, keywords in context_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                return context
        
        return "general content"
    
    def _validate_patterns(self, patterns: List[str], html: str) -> List[str]:
        """Validate discovered patterns against actual HTML using BeautifulSoup."""
        valid_patterns = []
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            for pattern in patterns:
                try:
                    # Test CSS selector
                    if pattern.startswith('/'):
                        # XPath pattern - skip validation for now
                        valid_patterns.append(pattern)
                    else:
                        # CSS selector
                        elements = soup.select(pattern)
                        if elements:  # Pattern found elements
                            valid_patterns.append(pattern)
                except Exception:
                    # Invalid pattern, skip
                    continue
                    
        except Exception as e:
            logger.warning(f"Failed to validate patterns: {e}")
            # Return all patterns if validation fails
            return patterns
        
        return valid_patterns
    
    def _merge_discoveries(
        self, 
        existing: DiscoveredFacts, 
        new_patterns: List[str],
        pattern_confidences: Dict[str, float],
        understanding: str
    ) -> DiscoveredFacts:
        """Intelligently merge new patterns with existing knowledge."""
        
        # Start with existing facts
        merged_patterns = existing.structural_patterns.copy()
        merged_confidences = existing.confidence_scores.copy()
        
        # Add new patterns
        for pattern in new_patterns:
            confidence = pattern_confidences.get(pattern, 0.5)
            
            if pattern in merged_confidences:
                # Update confidence with exponential moving average
                old_confidence = merged_confidences[pattern]
                merged_confidences[pattern] = 0.7 * old_confidence + 0.3 * confidence
            else:
                # New pattern
                merged_patterns.append(pattern)
                merged_confidences[pattern] = confidence
        
        # Update understanding
        updated_understanding = understanding if understanding else existing.page_understanding
        
        return DiscoveredFacts(
            structural_patterns=merged_patterns,
            confidence_scores=merged_confidences,
            page_understanding=updated_understanding,
            discarded_hypotheses=existing.discarded_hypotheses.copy(),
            new_discoveries=[f"{p}: {pattern_confidences.get(p, 0.5)}" for p in new_patterns]
        )
    
    def _needs_compression(self, facts: DiscoveredFacts) -> bool:
        """Check if memory compression is needed."""
        return len(facts.structural_patterns) > self.compression_threshold
