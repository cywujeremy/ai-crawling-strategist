"""DOM parsing utilities using BeautifulSoup."""

from bs4 import BeautifulSoup, Tag
from typing import Optional, List, Dict, Any
import re


def parse_html(html_content: str, parser: str = 'html.parser') -> Optional[BeautifulSoup]:
    """
    Safely parse HTML content with error handling.
    
    Args:
        html_content: HTML string to parse
        parser: BeautifulSoup parser to use ('html.parser', 'lxml', etc.)
        
    Returns:
        BeautifulSoup object or None if parsing fails
    """
    if not html_content or not html_content.strip():
        return None
    
    try:
        soup = BeautifulSoup(html_content, parser)
        return soup
    except Exception:
        # Fallback to more lenient parser
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception:
            return None


def validate_html_structure(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Validate that HTML structure is well-formed after processing.
    
    Args:
        soup: BeautifulSoup object to validate
        
    Returns:
        Dictionary with validation results
    """
    if not soup:
        return {'is_valid': False, 'errors': ['Empty or invalid soup object']}
    
    errors = []
    
    # Check for basic structure
    if not soup.find():
        errors.append('No HTML tags found')
    
    # Check for unclosed tags (BeautifulSoup usually handles this)
    # This is more of a sanity check
    all_tags = soup.find_all()
    if not all_tags:
        errors.append('No tags found after parsing')
    
    # Check for excessive nesting (potential parsing issues)
    max_depth = _get_max_depth(soup)
    if max_depth > 50:  # Arbitrary threshold
        errors.append(f'Excessive nesting depth: {max_depth}')
    
    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
        'tag_count': len(all_tags),
        'max_depth': max_depth
    }


def get_dom_stats(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Get statistics about DOM structure.
    
    Args:
        soup: BeautifulSoup object to analyze
        
    Returns:
        Dictionary with DOM statistics
    """
    if not soup:
        return {'error': 'Invalid soup object'}
    
    all_tags = soup.find_all()
    
    # Count tag types
    tag_counts = {}
    for tag in all_tags:
        tag_name = tag.name
        tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1
    
    # Get text content stats
    text_content = soup.get_text(strip=True)
    
    return {
        'total_tags': len(all_tags),
        'unique_tag_types': len(tag_counts),
        'tag_distribution': tag_counts,
        'text_length': len(text_content),
        'max_depth': _get_max_depth(soup)
    }


def extract_text_content(soup: BeautifulSoup, preserve_structure: bool = False) -> str:
    """
    Extract clean text content from HTML.
    
    Args:
        soup: BeautifulSoup object
        preserve_structure: Whether to preserve some structural spacing
        
    Returns:
        Clean text content
    """
    if not soup:
        return ""
    
    if preserve_structure:
        # Add newlines around block elements
        block_elements = ['div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                         'section', 'article', 'li', 'tr']
        
        for tag_name in block_elements:
            for tag in soup.find_all(tag_name):
                if tag.string:
                    tag.string.replace_with(f"\n{tag.string}\n")
    
    text = soup.get_text(separator=' ', strip=True)
    
    # Clean up excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def find_elements_by_pattern(soup: BeautifulSoup, pattern: str, 
                           attribute: str = 'class') -> List[Tag]:
    """
    Find elements matching a pattern in specified attribute.
    
    Args:
        soup: BeautifulSoup object to search
        pattern: Regex pattern to match
        attribute: Attribute to search in ('class', 'id', etc.)
        
    Returns:
        List of matching Tag objects
    """
    if not soup:
        return []
    
    matching_tags = []
    regex = re.compile(pattern, re.IGNORECASE)
    
    for tag in soup.find_all():
        if hasattr(tag, 'attrs') and tag.attrs:
            attr_value = tag.attrs.get(attribute)
            if attr_value:
                # Handle both string and list values (like class)
                if isinstance(attr_value, list):
                    attr_value = ' '.join(attr_value)
                
                if regex.search(attr_value):
                    matching_tags.append(tag)
    
    return matching_tags


def _get_max_depth(element, current_depth: int = 0) -> int:
    """
    Recursively calculate maximum nesting depth of DOM tree.
    
    Args:
        element: BeautifulSoup element to analyze
        current_depth: Current depth in recursion
        
    Returns:
        Maximum depth found
    """
    if not hasattr(element, 'children'):
        return current_depth
    
    max_child_depth = current_depth
    
    for child in element.children:
        if hasattr(child, 'name') and child.name:  # Skip text nodes
            child_depth = _get_max_depth(child, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)
    
    return max_child_depth


def is_likely_content_container(tag: Tag) -> bool:
    """
    Heuristic to determine if a tag likely contains content worth extracting.
    
    Args:
        tag: BeautifulSoup Tag object to evaluate
        
    Returns:
        True if tag likely contains extractable content
    """
    if not tag or not hasattr(tag, 'name'):
        return False
    
    # Content-bearing tag types
    content_tags = {
        'article', 'section', 'main', 'div', 'p', 'span',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'table', 'tr', 'td', 'th'
    }
    
    if tag.name not in content_tags:
        return False
    
    # Check if tag has meaningful text content
    text = tag.get_text(strip=True)
    if len(text) < 10:  # Arbitrary minimum content length
        return False
    
    # Check for common content indicators in class/id
    classes = ' '.join(tag.get('class', []))
    tag_id = tag.get('id', '')
    
    content_indicators = [
        'content', 'main', 'article', 'post', 'entry',
        'product', 'item', 'listing', 'card', 'tile'
    ]
    
    combined_attrs = f"{classes} {tag_id}".lower()
    
    for indicator in content_indicators:
        if indicator in combined_attrs:
            return True
    
    return True  # Default to True for content tags with sufficient text
