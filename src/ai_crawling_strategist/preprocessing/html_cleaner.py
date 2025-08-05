"""HTML cleaning and filtering for preprocessing."""

from bs4 import BeautifulSoup, Comment
from typing import Optional


# Tags that never contain extraction-relevant data
IRRELEVANT_TAGS = [
    # Code & Scripts
    'script', 'style', 'noscript',
    
    # Document metadata
    'head', 'meta', 'title', 'link',
    
    # Navigation and UI
    'nav', 'header', 'footer',
]

# Attributes that add noise without extraction value
IRRELEVANT_ATTRIBUTES = [
    'style',     # Inline CSS
    'onclick',   # JavaScript events  
    'onload',    # JavaScript events
    'onmouseover', 'onmouseout',  # Mouse events
    'data-analytics',  # Analytics tracking
    'data-track',      # Tracking attributes
]

# Attributes to preserve (whitelist approach for data-* attributes)
PRESERVE_DATA_ATTRIBUTES = [
    'data-testid',
    'data-cy',
    'data-test',
    'data-id',
]


def clean_html(raw_html: str, preserve_structure: bool = True) -> str:
    """
    Clean HTML by removing irrelevant tags and attributes.
    
    Args:
        raw_html: Raw HTML content to clean
        preserve_structure: Whether to keep structural tags even if empty
        
    Returns:
        Cleaned HTML string with reduced token count
    """
    if not raw_html or not raw_html.strip():
        return ""
    
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Remove irrelevant tags completely
    _remove_irrelevant_tags(soup)
    
    # Clean up attributes
    _clean_attributes(soup)
    
    # Remove comments
    _remove_comments(soup)
    
    # Remove empty tags if not preserving structure
    if not preserve_structure:
        _remove_empty_tags(soup)
    
    return str(soup)


def _remove_irrelevant_tags(soup: BeautifulSoup) -> None:
    """Remove tags that never contain extraction-relevant data."""
    for tag_name in IRRELEVANT_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()


def _clean_attributes(soup: BeautifulSoup) -> None:
    """Remove irrelevant attributes while preserving essential ones."""
    for tag in soup.find_all():
        if not tag.attrs:
            continue
            
        # Get list of attributes to remove
        attrs_to_remove = []
        
        for attr in tag.attrs:
            if attr in IRRELEVANT_ATTRIBUTES:
                attrs_to_remove.append(attr)
            elif attr.startswith('data-') and attr not in PRESERVE_DATA_ATTRIBUTES:
                # Remove most data-* attributes except whitelisted ones
                attrs_to_remove.append(attr)
        
        # Remove the attributes
        for attr in attrs_to_remove:
            del tag.attrs[attr]


def _remove_comments(soup: BeautifulSoup) -> None:
    """Remove HTML comments and processing instructions."""
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()


def _remove_empty_tags(soup: BeautifulSoup) -> None:
    """Remove tags that have no content after cleaning."""
    # Tags that should be preserved even if empty (structural importance)
    preserve_if_empty = {'div', 'section', 'article', 'main', 'aside', 'ul', 'ol', 'table'}
    
    # Iteratively remove empty tags (may create new empty tags)
    changed = True
    while changed:
        changed = False
        for tag in soup.find_all():
            if (tag.name not in preserve_if_empty and 
                not tag.get_text(strip=True) and 
                not tag.find_all()):
                tag.decompose()
                changed = True


def get_cleaning_stats(original_html: str, cleaned_html: str) -> dict:
    """
    Get statistics about the cleaning process.
    
    Args:
        original_html: Original HTML content
        cleaned_html: Cleaned HTML content
        
    Returns:
        Dictionary with cleaning statistics
    """
    original_size = len(original_html)
    cleaned_size = len(cleaned_html)
    
    if original_size == 0:
        reduction_percent = 0
    else:
        reduction_percent = ((original_size - cleaned_size) / original_size) * 100
    
    return {
        'original_size': original_size,
        'cleaned_size': cleaned_size,
        'size_reduction': original_size - cleaned_size,
        'reduction_percent': round(reduction_percent, 2)
    }
