"""DOM chunking engine for splitting large HTML documents into manageable pieces."""

from typing import List, Optional
import re
from bs4 import BeautifulSoup, NavigableString

from ..models.chunks import DOMChunk, ChunkContext, ChunkBoundary
from ..exceptions import ConfigurationError


class ProcessingError(Exception):
    """Base class for core processing errors."""
    pass


class ChunkingError(ProcessingError):
    """DOM chunking failures."""
    pass


class DOMChunker:
    """
    Splits large DOM trees into manageable chunks while preserving structure.
    
    Core principles:
    - Respect tag boundaries (never cut mid-tag)
    - Track parent context across chunks
    - Maintain consistent chunk sizes
    - Preserve structural integrity
    """
    
    def __init__(self, chunk_size: int = 2000, overlap_tokens: int = 100):
        """
        Configure chunking strategy.
        
        Args:
            chunk_size: Target tokens per chunk
            overlap_tokens: Context overlap between chunks
        """
        if chunk_size < 100:
            raise ConfigurationError("Chunk size must be at least 100 tokens")
        if overlap_tokens >= chunk_size // 2:
            raise ConfigurationError("Overlap tokens should be less than half of chunk size")
            
        self.chunk_size = chunk_size
        self.overlap_tokens = overlap_tokens
    
    def chunk_dom(
        self, 
        cleaned_html: str, 
        preserve_context: bool = True
    ) -> List[DOMChunk]:
        """
        Split DOM into chunks with context preservation.
        
        Algorithm:
        1. Parse HTML into BeautifulSoup tree
        2. Traverse DOM depth-first
        3. Accumulate elements until chunk_size reached
        4. Find next complete tag closure
        5. Record parent context stack
        6. Create chunk with position information
        
        Args:
            cleaned_html: Preprocessed HTML from html_cleaner
            preserve_context: Whether to track parent element stack
            
        Returns:
            List[DOMChunk]: Ordered chunks with context information
        """
        try:
            soup = BeautifulSoup(cleaned_html, 'html.parser')
        except Exception as e:
            raise ChunkingError(f"Failed to parse HTML: {e}")
        
        chunks = []
        current_html = ""
        current_position = 0
        chunk_index = 0
        context_stack = []
        
        # Calculate total estimated chunks for metadata
        total_estimated_tokens = self._estimate_tokens(cleaned_html)
        total_chunks = max(1, (total_estimated_tokens + self.chunk_size - 1) // self.chunk_size)
        
        for element in soup.descendants:
            if isinstance(element, NavigableString):
                # Add text content
                text = str(element).strip()
                if text:
                    current_html += text
            else:
                # Handle tag elements
                element_html = str(element)
                
                # Check if adding this element would exceed chunk size
                test_html = current_html + element_html
                if self._estimate_tokens(test_html) > self.chunk_size and current_html:
                    # Create chunk with current content
                    chunk = self._create_chunk(
                        chunk_id=f"chunk_{chunk_index}",
                        html_content=current_html,
                        chunk_index=chunk_index,
                        total_chunks=total_chunks,
                        start_position=current_position,
                        context_stack=context_stack if preserve_context else [],
                        cleaned_html=cleaned_html
                    )
                    chunks.append(chunk)
                    
                    # Setup for next chunk with overlap
                    current_position += len(current_html)
                    current_html = self._create_overlap_content(current_html, element_html)
                    chunk_index += 1
                else:
                    current_html += element_html
                
                # Update context stack
                if preserve_context:
                    self._update_context_stack(context_stack, element)
        
        # Create final chunk if there's remaining content
        if current_html.strip():
            chunk = self._create_chunk(
                chunk_id=f"chunk_{chunk_index}",
                html_content=current_html,
                chunk_index=chunk_index,
                total_chunks=max(total_chunks, chunk_index + 1),
                start_position=current_position,
                context_stack=context_stack if preserve_context else [],
                cleaned_html=cleaned_html
            )
            chunks.append(chunk)
        
        # Update total_chunks in all chunks
        actual_total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = actual_total
        
        return chunks
    
    def _create_chunk(
        self,
        chunk_id: str,
        html_content: str,
        chunk_index: int,
        total_chunks: int,
        start_position: int,
        context_stack: List[str],
        cleaned_html: str
    ) -> DOMChunk:
        """Create a DOMChunk with proper context and boundary information."""
        
        # Clean up chunk content and find safe boundaries
        cleaned_content = self._ensure_valid_html(html_content)
        end_position = start_position + len(cleaned_content)
        
        # Extract context information
        context = self._extract_parent_context(context_stack)
        
        # Create boundary information
        boundary = ChunkBoundary(
            start_position=start_position,
            end_position=end_position,
            start_tag_complete=True,  # We ensure this in _ensure_valid_html
            end_tag_complete=True,
            boundary_type="tag_boundary"
        )
        
        return DOMChunk(
            chunk_id=chunk_id,
            html_content=cleaned_content,
            context=context,
            boundary=boundary,
            chunk_index=chunk_index,
            total_chunks=total_chunks,
            metadata={
                "original_size": len(html_content),
                "cleaned_size": len(cleaned_content),
                "estimated_tokens": self._estimate_tokens(cleaned_content)
            }
        )
    
    def _extract_parent_context(self, context_stack: List[str]) -> ChunkContext:
        """Build parent tag stack for context preservation."""
        context = ChunkContext()
        
        for tag_info in context_stack:
            # Simple tag name extraction for now
            tag_name = tag_info.split('<')[1].split()[0].rstrip('>')
            context.add_parent_tag(tag_name)
        
        # Generate DOM path
        if context.open_parent_tags:
            context.dom_path = ' > '.join(context.open_parent_tags)
        
        return context
    
    def _update_context_stack(self, context_stack: List[str], element):
        """Update context stack based on current element."""
        if hasattr(element, 'name') and element.name:
            tag_html = f"<{element.name}>"
            
            # Add opening tag
            if not element.is_empty_element:
                context_stack.append(tag_html)
            
            # Handle self-closing tags
            if element.is_empty_element or element.name in ['br', 'hr', 'img', 'input', 'meta', 'link']:
                return
            
            # Remove from stack when we encounter closing (handled in parsing)
    
    def _create_overlap_content(self, current_html: str, next_element_html: str) -> str:
        """Create overlap content for context continuity between chunks."""
        if self.overlap_tokens <= 0:
            return next_element_html
        
        # Take last N tokens worth of content as overlap
        overlap_chars = self.overlap_tokens * 4  # Rough estimation: 4 chars per token
        if len(current_html) > overlap_chars:
            overlap_start = len(current_html) - overlap_chars
            # Find safe start point (beginning of a tag)
            safe_start = self._find_safe_cutpoint(current_html, overlap_start, forward=True)
            overlap_content = current_html[safe_start:]
        else:
            overlap_content = current_html
        
        return overlap_content + next_element_html
    
    def _find_safe_cutpoint(self, html_fragment: str, position: int, forward: bool = True) -> int:
        """Find next complete tag closure for clean chunk boundaries."""
        if forward:
            # Find next opening tag
            next_tag = html_fragment.find('<', position)
            return next_tag if next_tag != -1 else position
        else:
            # Find previous closing tag
            prev_tag_end = html_fragment.rfind('>', 0, position)
            return prev_tag_end + 1 if prev_tag_end != -1 else 0
    
    def _ensure_valid_html(self, html_content: str) -> str:
        """Ensure HTML chunk has valid structure."""
        try:
            # Parse and reserialize to fix any malformed HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            return str(soup)
        except Exception:
            # Fallback: return original content if parsing fails
            return html_content
    
    def _estimate_tokens(self, html_content: str) -> int:
        """Rough token estimation for chunk sizing."""
        # Remove HTML tags for better estimation
        text_content = re.sub(r'<[^>]+>', '', html_content)
        # Rough estimation: ~4 characters per token
        return len(text_content) // 4
