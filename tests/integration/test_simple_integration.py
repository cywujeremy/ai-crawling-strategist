"""
Simple integration test for AI Crawling Strategist.

Tests the complete DOM analysis pipeline on a real website to extract location addresses.
"""

import pytest
import os
from pathlib import Path
from ai_crawling_strategist import DOMStrategist


class TestSimpleIntegration:
    """Integration tests for the complete DOM analysis pipeline."""
    
    def test_extract_location_addresses_from_lindenmeyr_munroe(self):
        """
        Test extracting location addresses from Lindenmeyr Munroe locations page.
        
        This test validates the complete pipeline:
        1. HTML preprocessing and cleaning
        2. DOM chunking with context preservation
        3. Rolling memory management across chunks
        4. LLM-powered pattern discovery
        5. Final extraction schema generation
        
        Source: Local HTML file from Lindenmeyr Munroe locations page
        User Query: Extract all location addresses including street address, city, state, and zip code
        """
        # Path to the local HTML file
        html_file_path = r"C:\Users\CWu\Downloads\Locations - Lindenmeyr Munroe.html"
        
        # Check if the file exists
        if not os.path.exists(html_file_path):
            pytest.skip(f"HTML file not found at: {html_file_path}")
        
        # Read the HTML content from the local file
        try:
            with open(html_file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            print(f"Successfully loaded HTML content from local file: {len(html_content)} characters")
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(html_file_path, 'r', encoding='latin-1') as file:
                html_content = file.read()
            print(f"Successfully loaded HTML content with latin-1 encoding: {len(html_content)} characters")
        except Exception as e:
            pytest.fail(f"Failed to read HTML file: {e}")
        
        # Define the extraction query in natural language
        user_query = "Extract all location addresses including street address, city, state, and zip code"
        
        # Initialize the DOM Strategist
        # Note: This requires valid AWS credentials to be configured
        strategist = DOMStrategist(
            aws_region="us-east-1",
            chunk_size=2000,
            confidence_threshold=0.8,
            enable_validation=True
        )
        
        # Perform the analysis
        extraction_schema = strategist.analyze(
            html_content=html_content,
            query=user_query,
            preserve_context=True
        )
        
        # Validate the extraction schema structure
        assert extraction_schema is not None, "Extraction schema should not be None"
        assert hasattr(extraction_schema, 'container'), "Schema should have container selector"
        assert hasattr(extraction_schema, 'item'), "Schema should have item selector"
        assert hasattr(extraction_schema, 'fields'), "Schema should have field selectors"
        assert hasattr(extraction_schema, 'schema_confidence'), "Schema should have confidence score"
        
        # Validate confidence threshold
        assert extraction_schema.schema_confidence >= 0.0, "Confidence should be non-negative"
        assert extraction_schema.schema_confidence <= 1.0, "Confidence should not exceed 1.0"
        
        # Validate field mappings for address components
        expected_address_fields = {'address', 'street', 'city', 'state', 'zip', 'location'}
        schema_fields = set(extraction_schema.fields.keys())
        
        # Check that at least some address-related fields were identified
        address_field_overlap = expected_address_fields.intersection(
            {field.lower() for field in schema_fields}
        )
        assert len(address_field_overlap) > 0, (
            f"Expected to find address-related fields. "
            f"Found fields: {list(schema_fields)}, "
            f"Expected overlap with: {list(expected_address_fields)}"
        )
        
        # Validate selector format and structure
        assert extraction_schema.container.selector, "Container selector should not be empty"
        assert extraction_schema.item.selector, "Item selector should not be empty"
        
        for field_name, field_selector in extraction_schema.fields.items():
            assert field_selector.primary_selector, f"Primary selector for {field_name} should not be empty"
            assert field_selector.confidence >= 0.0, f"Field confidence for {field_name} should be non-negative"
            assert field_selector.confidence <= 1.0, f"Field confidence for {field_name} should not exceed 1.0"
        
        # Print results for manual verification
        print(f"\n=== EXTRACTION SCHEMA RESULTS ===")
        print(f"Overall Confidence: {extraction_schema.schema_confidence:.2f}")
        print(f"Container Selector: {extraction_schema.container.selector}")
        print(f"Item Selector: {extraction_schema.item.selector}")
        print(f"\nField Mappings:")
        for field_name, field_selector in extraction_schema.fields.items():
            print(f"  {field_name}: {field_selector.primary_selector} (confidence: {field_selector.confidence:.2f})")
        
        if hasattr(extraction_schema, 'strategy_explanation'):
            print(f"\nStrategy Explanation: {extraction_schema.strategy_explanation}")
        
        print(f"\n=== TEST PASSED ===")
        print(f"Successfully generated extraction schema for location addresses")


@pytest.mark.integration
@pytest.mark.slow
def test_integration_with_aws_auth_error_handling():
    """
    Test that proper error handling occurs when AWS credentials are not configured.
    
    This test validates graceful error handling for missing AWS configuration.
    """
    # Attempt to initialize without AWS credentials
    with pytest.raises(Exception) as exc_info:
        strategist = DOMStrategist(
            aws_access_key_id="invalid",
            aws_secret_access_key="invalid", 
            aws_region="us-east-1",
            enable_validation=True
        )
    
    # Verify that configuration errors are properly raised
    error_message = str(exc_info.value).lower()
    assert any(keyword in error_message for keyword in ['credential', 'authentication', 'aws', 'configuration']), (
        f"Expected authentication-related error, got: {exc_info.value}"
    )


if __name__ == "__main__":
    # Run the integration test directly
    test_instance = TestSimpleIntegration()
    test_instance.test_extract_location_addresses_from_lindenmeyr_munroe()
