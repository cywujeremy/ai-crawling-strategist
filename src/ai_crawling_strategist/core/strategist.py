"""Main orchestrator for DOM analysis and extraction schema generation."""

from typing import Optional
import logging
from tqdm import tqdm

from ..auth import CredentialResolver, AWSCredentials
from ..preprocessing import clean_html
from ..llm import ClaudeClient
from ..models.extraction import ExtractionSchema
from ..exceptions import (
    ConfigurationError, 
    ProcessingError, 
    LLMError,
    ChunkingError, 
    MemoryError, 
    SchemaGenerationError
)
from .chunker import DOMChunker
from .memory_manager import MemoryManager  
from .schema_generator import SchemaGenerator


logger = logging.getLogger(__name__)


class DOMStrategist:
    """
    Main orchestrator for DOM analysis and extraction schema generation.
    
    Coordinates all modules to provide a simple API for complex DOM processing.
    """
    
    def __init__(
        self,
        aws_profile: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: str = "us-east-1",
        chunk_size: int = 2000,
        confidence_threshold: float = 0.8,
        enable_validation: bool = True
    ):
        """
        Initialize strategist with AWS credentials and processing configuration.
        
        Args:
            aws_profile: AWS profile name for authentication
            aws_access_key_id: Direct AWS access key (overrides profile)
            aws_secret_access_key: Direct AWS secret key
            aws_region: AWS region for Claude Sonnet 3.5
            chunk_size: Target tokens per chunk
            confidence_threshold: Minimum confidence for pattern inclusion
            enable_validation: Test credentials on initialization
        """
        try:
            # Initialize credential resolver
            resolver = CredentialResolver()
            self.credentials = resolver.resolve(
                aws_profile=aws_profile,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_region=aws_region
            )
            
            # Initialize processing configuration
            self.chunk_size = chunk_size
            self.confidence_threshold = confidence_threshold
            self.enable_validation = enable_validation
            
            # Initialize components
            self.chunker = DOMChunker(chunk_size=chunk_size)
            self.llm_client = ClaudeClient(credentials=self.credentials)
            self.memory_manager = MemoryManager(
                llm_client=self.llm_client,
                confidence_threshold=confidence_threshold
            )
            self.schema_generator = SchemaGenerator(
                llm_client=self.llm_client,
                confidence_threshold=confidence_threshold
            )
            
            # Validate credentials if requested
            if enable_validation:
                self._validate_setup()
            
            logger.info("DOMStrategist initialized successfully")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize DOMStrategist: {e}")
    
    def analyze(
        self, 
        html_content: str, 
        query: str,
        preserve_context: bool = True
    ) -> ExtractionSchema:
        """
        Main analysis method - processes HTML and returns extraction schema.
        
        Args:
            html_content: Raw HTML to analyze
            query: Natural language extraction intent
            preserve_context: Whether to maintain DOM context across chunks
            
        Returns:
            ExtractionSchema: Complete extraction plan for crawl4ai
            
        Raises:
            ConfigurationError: AWS authentication or region issues
            ProcessingError: HTML parsing or chunking failures
            LLMError: Claude API failures or validation errors
        """
        try:
            logger.info(f"Starting analysis: {len(html_content)} chars, query: {query[:50]}...")
            
            # Step 1: Preprocess HTML
            logger.info("Preprocessing HTML content")
            cleaned_html = clean_html(html_content)
            logger.info(f"HTML cleaned: {len(html_content)} -> {len(cleaned_html)} chars")
            
            # Step 2: Chunk DOM
            logger.info("Chunking DOM into manageable pieces")
            chunks = self.chunker.chunk_dom(cleaned_html, preserve_context=preserve_context)
            logger.info(f"Created {len(chunks)} chunks")
            
            # Step 3: Initialize memory
            logger.info("Initializing memory with user intent")
            current_memory = self.memory_manager.initialize_memory(query)
            
            # Update total chunks in memory
            current_memory.total_chunks = len(chunks)
            
            # Step 4: Process chunks iteratively with progress tracking
            logger.info("Processing chunks with LLM analysis")
            with tqdm(total=len(chunks), desc="Analyzing chunks") as pbar:
                for chunk in chunks:
                    # Update chunk total_chunks if needed
                    chunk.total_chunks = len(chunks)
                    
                    # Process chunk and update memory
                    memory_output = self.memory_manager.process_chunk(chunk, current_memory)
                    
                    # Prepare memory for next chunk (compress if needed)
                    if chunk.chunk_index < len(chunks) - 1:  # Not the last chunk
                        current_memory = self.memory_manager.compress_memory(memory_output)
                    
                    pbar.update(1)
                    pbar.set_postfix({
                        'patterns': len(memory_output.updated_facts.structural_patterns),
                        'confidence': f"{max(memory_output.updated_facts.confidence_scores.values(), default=0):.2f}"
                    })
            
            final_memory = memory_output
            
            # Step 5: Generate final schema
            logger.info("Generating final extraction schema")
            schema = self.schema_generator.generate_schema(
                final_memory=final_memory,
                user_query=query,
                source_html=cleaned_html if self.enable_validation else None
            )
            
            logger.info(f"Analysis complete: confidence={schema.schema_confidence:.2f}")
            return schema
            
        except ChunkingError as e:
            logger.error(f"Chunking failed: {e}")
            return self._fallback_analysis(html_content, query)
        except MemoryError as e:
            logger.error(f"Memory processing failed: {e}")
            return self._simplified_analysis(html_content, query)
        except SchemaGenerationError as e:
            logger.error(f"Schema generation failed: {e}")
            return self._basic_schema_fallback(query)
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise ProcessingError(f"Analysis failed: {e}")
    
    def _validate_setup(self):
        """Validate AWS credentials and Claude access."""
        try:
            # Test Claude API access with minimal request
            test_response = self.llm_client.call_claude(
                prompt="Test connection. Respond with 'OK'.",
                max_tokens=10,
                temperature=0
            )
            
            if "OK" not in test_response:
                raise ConfigurationError("Claude API test failed")
            
            logger.info("Credentials validated successfully")
            
        except Exception as e:
            raise ConfigurationError(f"Credential validation failed: {e}")
    
    def _fallback_analysis(self, html_content: str, query: str) -> ExtractionSchema:
        """Fallback analysis when chunking fails."""
        logger.info("Attempting fallback analysis with simplified chunking")
        
        try:
            # Try with simpler chunking strategy
            simple_chunker = DOMChunker(chunk_size=self.chunk_size * 2)  # Larger chunks
            cleaned_html = clean_html(html_content)
            chunks = simple_chunker.chunk_dom(cleaned_html, preserve_context=False)
            
            # Process with simplified approach
            current_memory = self.memory_manager.initialize_memory(query)
            current_memory.total_chunks = len(chunks)
            
            for chunk in chunks[:3]:  # Limit to first 3 chunks
                chunk.total_chunks = len(chunks)
                memory_output = self.memory_manager.process_chunk(chunk, current_memory)
                current_memory = self.memory_manager.compress_memory(memory_output)
            
            return self.schema_generator.generate_schema(
                final_memory=memory_output,
                user_query=query
            )
            
        except Exception as e:
            logger.error(f"Fallback analysis failed: {e}")
            return self._simplified_analysis(html_content, query)
    
    def _simplified_analysis(self, html_content: str, query: str) -> ExtractionSchema:
        """Simplified analysis for single chunk processing."""
        logger.info("Attempting simplified single-chunk analysis")
        
        try:
            # Clean HTML and treat as single chunk
            cleaned_html = clean_html(html_content)
            
            # Truncate if too large
            max_single_chunk = self.chunk_size * 3
            if len(cleaned_html) > max_single_chunk:
                cleaned_html = cleaned_html[:max_single_chunk]
            
            # Create single chunk manually
            from ..models.chunks import DOMChunk, ChunkBoundary, ChunkContext
            
            chunk = DOMChunk(
                chunk_id="single_chunk",
                html_content=cleaned_html,
                context=ChunkContext(),
                boundary=ChunkBoundary(
                    start_position=0,
                    end_position=len(cleaned_html)
                ),
                chunk_index=0,
                total_chunks=1
            )
            
            # Process single chunk
            current_memory = self.memory_manager.initialize_memory(query)
            memory_output = self.memory_manager.process_chunk(chunk, current_memory)
            
            return self.schema_generator.generate_schema(
                final_memory=memory_output,
                user_query=query
            )
            
        except Exception as e:
            logger.error(f"Simplified analysis failed: {e}")
            return self._basic_schema_fallback(query)
    
    def _basic_schema_fallback(self, query: str) -> ExtractionSchema:
        """Basic schema generation without LLM analysis."""
        logger.info("Generating basic fallback schema")
        
        from ..models.extraction import (
            ContainerSelector, ItemSelector, FieldSelector, SelectorType
        )
        from ..models.memory import UserIntent
        
        # Extract target entities from query
        target_entities = self.memory_manager._extract_target_entities(query)
        
        # Create basic selectors
        container = ContainerSelector(
            selector="body",
            confidence=0.3,
            description="Fallback container selector"
        )
        
        item = ItemSelector(
            selector="div, article, section, li",
            confidence=0.3,
            description="Fallback item selector"
        )
        
        # Create basic field selectors
        fields = {}
        for entity in target_entities:
            default_selectors = self.schema_generator._get_default_selectors(entity)
            fields[entity] = FieldSelector(
                primary_selector=default_selectors["primary"],
                confidence=0.3,
                fallback_selectors=default_selectors["fallbacks"],
                field_description=f"Fallback selector for {entity}",
                extraction_method=self.schema_generator._get_extraction_method(entity),
                attribute_name=self.schema_generator._get_attribute_name(entity)
            )
        
        return ExtractionSchema(
            container=container,
            item=item,
            fields=fields,
            schema_confidence=0.3,
            strategy_explanation=(
                f"Fallback schema generated for query: '{query}'. "
                "This schema uses basic selectors and may require manual refinement."
            )
        )
