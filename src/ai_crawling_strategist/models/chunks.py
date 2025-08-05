"""DOM chunk data structures for incremental processing."""

from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from enum import Enum


class ChunkingStrategy(str, Enum):
    """Strategy for creating DOM chunks."""
    
    TOKEN_BASED = "token_based"
    CHARACTER_BASED = "character_based"
    TAG_BOUNDARY = "tag_boundary"
    SEMANTIC_BLOCKS = "semantic_blocks"


class ChunkContext(BaseModel):
    """Parent tag stack and DOM path information."""
    
    open_parent_tags: List[str] = Field(default_factory=list, description="Stack of unclosed parent element names")
    parent_attributes: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Attributes of open parent tags")
    dom_path: str = Field(default="", description="CSS selector or XPath to current position")
    nesting_level: int = Field(default=0,ge=0, description="Current nesting depth")
    previous_sibling_info: Optional[str] = Field(default=None, description="Information about previous sibling element")
    
    @validator('open_parent_tags')
    def tags_must_be_valid(cls, v):
        """Ensure all tag names are valid HTML tag names"""
        valid_chars = set('abcdefghijklmnopqrstuvwxyz0123456789-')
        for tag in v:
            if not tag or not all(c.lower() in valid_chars for c in tag):
                raise ValueError(f'Invalid tag name: {tag}')
        return v
    
    def add_parent_tag(self, tag_name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add a parent tag to the context stack."""
        self.open_parent_tags.append(tag_name)
        if attributes:
            self.parent_attributes[tag_name] = attributes
        self.nesting_level += 1
    
    def remove_parent_tag(self, tag_name: str):
        """Remove a parent tag from the context stack."""
        if tag_name in self.open_parent_tags:
            self.open_parent_tags.remove(tag_name)
            if tag_name in self.parent_attributes:
                del self.parent_attributes[tag_name]
            self.nesting_level = max(0, self.nesting_level - 1)
    
    def get_context_html(self) -> str:
        """Generate HTML representation of current context."""
        if not self.open_parent_tags:
            return ""
        
        context_parts = []
        for tag in self.open_parent_tags:
            attrs = self.parent_attributes.get(tag, {})
            if attrs:
                attr_str = ' '.join(f'{k}="{v}"' for k, v in attrs.items())
                context_parts.append(f"<{tag} {attr_str}>")
            else:
                context_parts.append(f"<{tag}>")
        
        return ''.join(context_parts)


class ChunkBoundary(BaseModel):
    """Information about chunk boundaries."""
    
    start_position: int = Field(ge=0, description="Starting character position in original HTML")
    end_position: int = Field(ge=0, description="Ending character position in original HTML")
    start_tag_complete: bool = Field(default=True, description="Whether chunk starts with complete tag")
    end_tag_complete: bool = Field(default=True, description="Whether chunk ends with complete tag")
    boundary_type: str = Field(default="tag_boundary", description="Type of boundary (tag_boundary, forced_split, etc.)")
    
    @validator('end_position')
    def end_must_be_after_start(cls, v, values):
        """Ensure end position is after start position"""
        if 'start_position' in values and v <= values['start_position']:
            raise ValueError('End position must be after start position')
        return v
    
    def get_length(self) -> int:
        """Get the length of the chunk in characters."""
        return self.end_position - self.start_position


class DOMChunk(BaseModel):
    """Individual chunk with HTML content and context."""
    
    chunk_id: str = Field(..., description="Unique identifier for this chunk")
    html_content: str = Field(..., description="HTML content of this chunk")
    context: ChunkContext = Field(default_factory=ChunkContext, description="DOM context information")
    boundary: ChunkBoundary = Field(..., description="Chunk boundary information")
    chunk_index: int = Field(ge=0, description="Index of this chunk in sequence")
    total_chunks: int = Field(ge=1, description="Total number of chunks in document")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional chunk metadata")
    
    @validator('chunk_index')
    def index_must_be_valid(cls, v, values):
        """Ensure chunk index is valid relative to total chunks"""
        if 'total_chunks' in values and v >= values['total_chunks']:
            raise ValueError('Chunk index must be less than total chunks')
        return v
    
    @validator('html_content')
    def html_must_not_be_empty(cls, v):
        """Ensure HTML content is not empty"""
        if not v.strip():
            raise ValueError('HTML content cannot be empty')
        return v
    
    def get_text_content(self) -> str:
        """Extract plain text content from HTML."""
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(self.html_content, 'html.parser')
            return soup.get_text(strip=True)
        except Exception:
            return ""
    
    def get_chunk_size(self, unit: str = "characters") -> int:
        """Get chunk size in specified unit."""
        if unit == "characters":
            return len(self.html_content)
        elif unit == "tokens":
            # Rough token estimation: ~4 characters per token
            return len(self.html_content) // 4
        elif unit == "text_characters":
            return len(self.get_text_content())
        else:
            raise ValueError(f"Unsupported unit: {unit}")
    
    def has_complete_tags(self) -> bool:
        """Check if chunk contains only complete HTML tags."""
        return self.boundary.start_tag_complete and self.boundary.end_tag_complete
    
    def is_first_chunk(self) -> bool:
        """Check if this is the first chunk in sequence."""
        return self.chunk_index == 0
    
    def is_last_chunk(self) -> bool:
        """Check if this is the last chunk in sequence."""
        return self.chunk_index == self.total_chunks - 1


class ChunkingConfig(BaseModel):
    """Configuration for chunking strategy."""
    
    strategy: ChunkingStrategy = Field(default=ChunkingStrategy.TOKEN_BASED, description="Chunking strategy to use")
    target_size: int = Field(default=2000, ge=100, description="Target chunk size (tokens or characters)")
    max_size: int = Field(default=3000, ge=100, description="Maximum allowed chunk size")
    min_size: int = Field(default=500, ge=50, description="Minimum chunk size before forced split")
    preserve_tag_boundaries: bool = Field(default=True, description="Respect HTML tag boundaries")
    preserve_semantic_blocks: bool = Field(default=False, description="Try to keep semantic elements together")
    overlap_size: int = Field(default=0, ge=0, description="Number of characters to overlap between chunks")
    
    @validator('max_size')
    def max_must_be_greater_than_target(cls, v, values):
        """Ensure max size is greater than target size"""
        if 'target_size' in values and v <= values['target_size']:
            raise ValueError('Max size must be greater than target size')
        return v
    
    @validator('min_size')
    def min_must_be_less_than_target(cls, v, values):
        """Ensure min size is less than target size"""
        if 'target_size' in values and v >= values['target_size']:
            raise ValueError('Min size must be less than target size')
        return v
    
    @validator('overlap_size')
    def overlap_must_be_reasonable(cls, v, values):
        """Ensure overlap size is not too large"""
        if 'target_size' in values and v >= values['target_size'] // 2:
            raise ValueError('Overlap size should be less than half of target size')
        return v
    
    def get_size_unit(self) -> str:
        """Get the unit of measurement for chunk sizes."""
        if self.strategy == ChunkingStrategy.TOKEN_BASED:
            return "tokens"
        elif self.strategy == ChunkingStrategy.CHARACTER_BASED:
            return "characters"
        else:
            return "logical_units"


class ChunkingResult(BaseModel):
    """Result of chunking a document."""
    
    chunks: List[DOMChunk] = Field(default_factory=list, description="List of generated chunks")
    config: ChunkingConfig = Field(..., description="Configuration used for chunking")
    original_size: int = Field(ge=0, description="Size of original document")
    total_chunks: int = Field(ge=0, description="Total number of chunks created")
    chunking_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about chunking process")
    
    @validator('total_chunks')
    def total_chunks_must_match_list(cls, v, values):
        """Ensure total_chunks matches actual chunk count"""
        if 'chunks' in values and v != len(values['chunks']):
            raise ValueError('Total chunks must match length of chunks list')
        return v
    
    def get_average_chunk_size(self) -> float:
        """Get average chunk size across all chunks."""
        if not self.chunks:
            return 0.0
        
        total_size = sum(chunk.get_chunk_size() for chunk in self.chunks)
        return total_size / len(self.chunks)
    
    def get_size_distribution(self) -> Dict[str, int]:
        """Get distribution of chunk sizes."""
        sizes = [chunk.get_chunk_size() for chunk in self.chunks]
        return {
            'min_size': min(sizes) if sizes else 0,
            'max_size': max(sizes) if sizes else 0,
            'avg_size': int(self.get_average_chunk_size()),
            'total_size': sum(sizes)
        }
    
    def validate_chunk_integrity(self) -> List[str]:
        """Validate that all chunks maintain HTML integrity."""
        issues = []
        
        for i, chunk in enumerate(self.chunks):
            if not chunk.has_complete_tags():
                issues.append(f"Chunk {i} has incomplete tags")
            
            if chunk.chunk_index != i:
                issues.append(f"Chunk {i} has incorrect index: {chunk.chunk_index}")
            
            if chunk.total_chunks != self.total_chunks:
                issues.append(f"Chunk {i} has incorrect total_chunks: {chunk.total_chunks}")
        
        return issues
