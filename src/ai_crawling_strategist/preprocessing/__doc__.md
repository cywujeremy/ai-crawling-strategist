# Preprocessing Module

## Purpose
Clean and filter HTML content before DOM chunking to reduce token usage and improve extraction accuracy.

## Key Components

### html_cleaner.py
Main preprocessing logic with configurable filtering strategies:

- **Tag Removal**: Strip irrelevant elements (script, style, meta, etc.)
- **Attribute Filtering**: Remove heavy attributes (style, onclick, data-*)
- **Comment Cleanup**: Remove HTML comments and processing instructions
- **Token Reduction**: Target 30-50% size reduction while preserving structure

### dom_parser.py  
BeautifulSoup utilities for robust DOM manipulation:

- **Safe Parsing**: Handle malformed HTML gracefully
- **Structure Validation**: Ensure tag integrity after cleaning
- **Context Preservation**: Maintain essential structural elements

## Implementation Strategy

1. **Configurable Filters**: Define removal patterns in constants for easy customization
2. **Preservation Rules**: Keep extraction-relevant tags (div, section, ul, h1-h6, etc.)
3. **Attribute Whitelist**: Preserve essential attributes (class, id, href, data-testid)
4. **Validation**: Verify cleaned HTML remains well-formed

## Output
Clean, token-optimized HTML ready for DOM chunking while preserving all extraction-relevant content.
