# 🧠 Incremental, Structure-Aware DOM Parsing with Rolling Memory

## 📌 Purpose

Given a webpage and a natural language instruction describing what information to extract (e.g., "extract all product listings with title and price"), the system should:

- Incrementally parse and traverse the DOM in chunks
- Use an LLM to analyze each chunk in context
- Maintain a **rolling memory** of previously learned extraction patterns
- Return a final extraction strategy that can be executed by `crawl4ai` (or optionally extended via simple loops)

---

## ✅ Goals

- **Avoid LLM token overload** by breaking large HTML into manageable, complete DOM chunks
- **Track the current DOM path** during traversal
- **Dynamically update memory** of what has been identified (e.g., listing container, field patterns)
- **Summarize a complete extraction schema** at the end, based on the full document scan

---

## 🧩 Core Features

| Feature               | Description |
|-----------------------|-------------|
| **DOM Chunking**      | Break the DOM into fixed-size chunks while respecting tag boundaries |
| **Rolling Memory**    | Keep an updated summary of learned patterns during traversal |
| **Context Tracking**  | Keep track of the current location in the DOM tree (e.g., XPath) |
| **Compression**       | Strip irrelevant tags/attributes to reduce token usage |
| **LLM Analysis**      | Use an LLM to read each chunk + memory, and return pattern updates |
| **Final Schema Output** | Output a complete, structured extraction plan for crawl4ai |

---

## 🔧 Technical Flow

1. **Input:**
   - Raw HTML
   - Natural language query (e.g., "extract job listings with title, location, salary")

2. **Process:**
   - **HTML Preprocessing**: Clean and filter irrelevant content
   - Parse HTML into a DOM tree
   - Chunk the DOM into structural blocks (preserve tag closure)
   - For each chunk:
     - Attach DOM path
     - Feed it into the LLM along with rolling memory
     - Get updated field mappings / extraction hints
   - Accumulate & compress memory after each chunk

3. **Output:**
   - A structured extraction plan consumable by `crawl4ai`

---

## 🧹 HTML Preprocessing

### Content Filtering Strategy
Before DOM parsing and chunking, filter out irrelevant elements that will never contain target data:

#### 🗑️ Elements to Remove
```python
IRRELEVANT_TAGS = [
    # Code & Scripts
    'script', 'style', 'noscript',
    
    # Document metadata
    'head', 'meta', 'title', 'link',
    
    # Comments and processing instructions
    # (handled by BeautifulSoup comment removal)
]

IRRELEVANT_ATTRIBUTES = [
    # Remove heavy attributes that don't help with extraction
    'style',     # Inline CSS
    'onclick',   # JavaScript events  
    'onload',    # JavaScript events
    'data-*',    # Most data attributes (keep data-testid, data-cy)
]
```

#### ✅ Content to Preserve
- **Structural tags**: `div`, `section`, `article`, `main`, `aside`
- **Data containers**: `ul`, `ol`, `li`, `table`, `tr`, `td`
- **Text elements**: `h1-h6`, `p`, `span`, `a`
- **Semantic tags**: `header`, `footer`, `nav` (for context)
- **Essential attributes**: `class`, `id`, `href`, `data-testid`

#### 🔧 Implementation Example
```python
from bs4 import BeautifulSoup, Comment

def preprocess_html(raw_html):
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Remove irrelevant tags
    for tag_name in IRRELEVANT_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    
    # Remove irrelevant attributes
    for tag in soup.find_all():
        for attr in IRRELEVANT_ATTRIBUTES:
            if attr.endswith('*'):  # Handle data-* pattern
                attrs_to_remove = [a for a in tag.attrs if a.startswith(attr[:-1])]
                for a in attrs_to_remove:
                    del tag.attrs[a]
            elif attr in tag.attrs:
                del tag.attrs[attr]
    
    # Remove comments
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()
    
    return str(soup)
```

### Benefits
- **Token reduction**: ~30-50% smaller HTML for LLM processing
- **Focus improvement**: LLM analyzes only extraction-relevant content  
- **Performance**: Faster DOM parsing and traversal
- **Accuracy**: Reduces noise in pattern discovery

---

## 🔄 DOM Chunking Strategy

### Core Principles
- **Fixed baseline chunk size** (e.g., ~2000 tokens) for consistent processing
- **Tag boundary respect**: Never cut in the middle of HTML tags (avoid `<di...v>`)
- **Complete tag endings**: Each chunk must end at a complete closing tag
- **Parent context preservation**: Can cut within parent tags, but track the context

### Chunking Logic
```
1. Start with target chunk size (tokens/characters)
2. Scan forward to find the next complete tag ending
3. Cut at that position, even if inside parent tags
4. Record current DOM context (open parent tags)
5. Pass context information to next chunk
```

### Context Tracking
For each chunk, maintain:
- **Open parent tags**: Stack of unclosed parent elements
- **DOM path**: Current XPath or CSS selector context  
- **Nesting level**: Depth in the DOM tree
- **Previous chunk summary**: Key patterns found in prior chunks

### Example
```html
<!-- Chunk 1 ends here -->
    </div>
  </section>
<!-- Context: Still inside <main><article> -->
<!-- Chunk 2 starts here -->
  <section class="products">
    <div class="product-item">
```

This approach ensures:
- ✅ HTML structure integrity
- ✅ Manageable chunk sizes  
- ✅ Clear context handoff
- ✅ No information loss at boundaries

---

## 🧠 Rolling Memory Management

### Memory Input (Per Chunk)
Each chunk processing receives:

```json
{
  "chunk_start_position": {
    "xpath": "//main/section[2]/div[1]",
    "nesting_context": "<main><section class='products'><div class='grid'>",
    "previous_chunk_end": "</div></section>"
  },
  "user_intent": {
    "original_query": "extract job listings with title, location, salary",
    "target_entities": ["title", "location", "salary"],
    "context": "job listings"
  },
  "discovered_facts": {
    "structural_patterns": [
      "Job containers: //div[@class='job-item']",
      "Title pattern: .//h2[@class='job-title']/text()",
      "Location found in: .//span[contains(@class,'location')]"
    ],
    "confidence_scores": {
      "job_container": 0.85,
      "title_selector": 0.92
    },
    "page_understanding": "Grid layout with job cards, consistent structure across items"
  }
}
```

### Memory Output (Per Chunk) 
Each chunk processing updates:

```json
{
  "chunk_end_position": {
    "xpath": "//main/section[2]/div[3]", 
    "nesting_context": "<main><section class='products'><div class='grid'>",
    "current_chunk_end": "</div></div>"
  },
  "user_intent": "[UNCHANGED - prevents hallucination drift]",
  "updated_facts": {
    "new_discoveries": [
      "Salary pattern confirmed: .//span[@class='salary-range']",
      "Date pattern: .//time[@class='posted-date']"
    ],
    "consolidated_patterns": [
      "Job containers: //div[@class='job-item'] (confidence: 0.95)",
      "Title: .//h2[@class='job-title']/text() (confidence: 0.92)",
      "Location: .//span[contains(@class,'location')] (confidence: 0.88)",
      "Salary: .//span[@class='salary-range'] (confidence: 0.82)"
    ],
    "refined_understanding": "Consistent job card structure, salary not always present",
    "discarded_hypotheses": ["Price in .product-price (irrelevant for jobs)"]
  }
}
```

### Memory Evolution Strategy

#### 🔄 Dynamic Fact Management
- **Accumulate**: Build pattern confidence through repetition
- **Refine**: Update selectors when better versions found  
- **Consolidate**: Merge similar patterns into robust selectors
- **Discard**: Remove irrelevant or low-confidence findings

#### 🎯 Anti-Hallucination Measures
- **Intent Anchoring**: User intent remains constant across chunks
- **Evidence-Based**: All patterns backed by actual HTML evidence
- **BeautifulSoup Validation**: Use DOM parsing to verify LLM claims
- **Confidence Tracking**: Maintain scores for pattern reliability

#### 📏 Memory Compression
**Prompt Engineering Guidelines:**
```
"Focus on extraction-relevant patterns. Discard decorative/navigation elements.
Consolidate similar selectors. Maintain only high-confidence discoveries.
If memory exceeds [X] items, prioritize: 
1. Direct matches to user intent
2. High-confidence patterns (>0.8)
3. Recent discoveries over old ones"
```

#### 🔧 Technical Implementation
- **Position Tracking**: BeautifulSoup to accurately track DOM position
- **Pattern Validation**: Test selectors against actual HTML before storing
- **Memory Pruning**: Automatic removal of outdated/irrelevant facts

---

## 🤖 LLM Integration & Prompt Engineering

### LLM Configuration
- **Model**: AWS Claude Sonnet 3.5
- **Approach**: Single-shot prompts (avoiding multi-step complexity)
- **Performance**: No current constraints on response time or cost

### Prompt Template Architecture

#### 🔄 Template 1: Chunk Processing & Memory Update
**Purpose**: Analyze current chunk + update rolling memory  
**Usage**: From first chunk to last chunk  
**Input**: Current chunk HTML + rolling memory + user intent  
**Output**: Updated memory structure (JSON)

```python
CHUNK_ANALYSIS_TEMPLATE = """
You are analyzing HTML chunk {chunk_index}/{total_chunks} for data extraction.

USER INTENT: {user_intent}

CURRENT POSITION: {chunk_start_position}

PREVIOUS DISCOVERIES: {discovered_facts}

CURRENT HTML CHUNK:
{html_chunk}

INSTRUCTIONS:
1. Analyze this chunk for patterns matching the user intent
2. Update the memory with new discoveries
3. Consolidate patterns with previous findings
4. Maintain confidence scores
5. Discard irrelevant information

OUTPUT FORMAT: [Pydantic schema enforced]
"""
```

#### 🎯 Template 2: Final Schema Generation  
**Purpose**: Convert final memory into crawl4ai extraction schema  
**Usage**: After all chunks processed  
**Input**: Final consolidated memory  
**Output**: Structured extraction plan

```python
SCHEMA_GENERATION_TEMPLATE = """
You are creating a final extraction schema based on discovered patterns.

CONSOLIDATED MEMORY: {final_memory}

USER INTENT: {user_intent}

INSTRUCTIONS:
1. Convert discovered patterns into crawl4ai-compatible selectors
2. Prioritize high-confidence patterns (>0.8)
3. Ensure selectors are robust and specific
4. Include fallback selectors when available

OUTPUT FORMAT: [Pydantic schema enforced]
"""
```

### Output Validation & Error Handling

#### 📋 Pydantic Schema Validation
```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class ChunkMemoryUpdate(BaseModel):
    chunk_end_position: Dict[str, str]
    user_intent: str  # Unchanged from input
    updated_facts: Dict[str, any]
    confidence_scores: Dict[str, float] = Field(ge=0.0, le=1.0)
    
class FinalExtractionSchema(BaseModel):
    container_selector: str
    item_selector: str  
    fields: Dict[str, str]
    fallback_selectors: Optional[Dict[str, List[str]]] = None
    confidence_summary: Dict[str, float]
```

#### 🔁 Retry Mechanism
```python
def process_chunk_with_retry(chunk_html, memory, max_retries=3):
    for attempt in range(max_retries):
        try:
            llm_response = call_claude(chunk_template, chunk_html, memory)
            validated_output = ChunkMemoryUpdate.parse_raw(llm_response)
            return validated_output
        except ValidationError as e:
            if attempt == max_retries - 1:
                raise Exception(f"JSON validation failed after {max_retries} retries: {e}")
            # Log error and retry
            continue
```

#### ✅ Validation Strategy
- **JSON Structure**: Pydantic model validation
- **Selector Testing**: BeautifulSoup validation against actual HTML  
- **Confidence Bounds**: Ensure scores between 0.0-1.0
- **Required Fields**: Enforce mandatory schema elements
- **Fallback Handling**: Graceful degradation for parsing failures

### Error Recovery
- **Malformed JSON**: Automatic retry with modified prompt
- **Invalid Selectors**: BeautifulSoup verification + correction
- **Memory Corruption**: Rollback to previous valid state
- **Complete Failure**: Fallback to basic pattern matching

---

## 📦 Output Format (Example)

```json
{
  "container_selector": "//div[@class='job-listing']",
  "item_selector": ".//div[@class='job-item']",
  "fields": {
    "title": ".//h2/text()",
    "location": ".//span[@class='location']/text()",
    "salary": ".//span[@class='salary']/text()"
  }
}
```

---

## 🔐 AWS Configuration Strategy

### Authentication Priority Order
The system should support multiple AWS credential configuration methods with the following priority hierarchy:

1. **AWS Profile (Highest Priority)**
   ```python
   strategist = DOMStrategist(aws_profile="production")
   # or use default profile if no profile specified
   strategist = DOMStrategist()  # Uses ~/.aws/credentials default profile
   ```

2. **Global Configuration (Fallback)**
   ```python
   import ai_crawling_strategist as acs
   acs.aws_access_key_id = "your-access-key"
   acs.aws_secret_access_key = "your-secret-key"
   acs.aws_region = "us-east-1"
   
   strategist = DOMStrategist()  # Uses global config
   ```

3. **Direct Parameters (Override)**
   ```python
   strategist = DOMStrategist(
       aws_access_key_id="your-access-key",
       aws_secret_access_key="your-secret-key",
       aws_region="us-east-1"
   )
   ```

4. **Environment Variables (System Level)**
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

### Configuration Resolution Logic
```python
def resolve_aws_config(
    aws_profile=None, 
    aws_access_key_id=None, 
    aws_secret_access_key=None,
    aws_region=None
):
    """
    1. If direct parameters provided, use them
    2. Else if aws_profile specified, load from AWS credentials file
    3. Else if global configuration exists, use it
    4. Else try default AWS profile (~/.aws/credentials)
    5. Else try environment variables
    6. Else raise configuration error with helpful message
    """
```

### Error Handling
- **Missing Credentials**: Clear error message with configuration instructions
- **Invalid Profile**: Specific error indicating profile not found in ~/.aws/credentials
- **Invalid Region**: Warning if region doesn't support Claude Sonnet 3.5
- **Connection Test**: Optional credential validation on initialization

### Package Interface Design
```python
from ai_crawling_strategist import DOMStrategist

# Simplest usage (relies on AWS profile or env vars)
strategist = DOMStrategist()

# With specific configuration
strategist = DOMStrategist(
    aws_profile="my-profile",
    chunk_size=3000,
    confidence_threshold=0.8
)

# Main analysis method
schema = strategist.analyze(
    html_content="<html>...</html>",
    query="extract job listings with title and salary"
)
```

---

## 📚 Additional Documentation

- **[Robustness Enhancements](./robustness-enhancements.md)**: Future considerations for edge cases and system resilience (not immediate priorities)
