# 🧠 AI Crawling Strategist

**Incremental DOM parsing with rolling memory for intelligent web data extraction**

## 💡 The Core Idea

Traditional web scraping tools require you to manually analyze HTML structure and write CSS/XPath selectors. But what if an AI could do this analysis for you?

**AI Crawling Strategist** solves the "cold start" problem of web scraping by using LLM-powered analysis to automatically discover extraction patterns from any webpage. Simply provide raw HTML and describe what you want to extract in natural language - the system will analyze the DOM structure incrementally and generate a complete extraction strategy that works with `crawl4ai` or other scraping frameworks.

### The Innovation: Rolling Memory Architecture

Instead of overwhelming an LLM with massive HTML documents, this system:

1. **Chunks the DOM** into manageable pieces while preserving structural boundaries
2. **Maintains rolling memory** of discovered patterns as it analyzes each chunk
3. **Evolves understanding** incrementally, building confidence in extraction strategies
4. **Generates robust selectors** based on patterns learned across the entire document

This approach enables analysis of arbitrarily large web pages while maintaining context and discovering reliable extraction patterns.

---

## 🚀 Key Features

| Feature | Description |
|---------|-------------|
| **🧩 Smart DOM Chunking** | Breaks large HTML into manageable pieces while respecting tag boundaries and preserving context |
| **🧠 Rolling Memory System** | Maintains and evolves extraction pattern knowledge across chunks with confidence scoring |
| **🎯 Natural Language Queries** | Describe what to extract in plain English: *"extract all product listings with title, price, and rating"* |
| **🔗 crawl4ai Integration** | Outputs production-ready extraction schemas compatible with crawl4ai |
| **☁️ AWS Claude Integration** | Powered by Claude Sonnet 3.5 via AWS Bedrock for reliable analysis |
| **🛡️ Robust Error Handling** | Graceful handling of malformed HTML, failed patterns, and edge cases |
| **📊 Confidence Scoring** | Each discovered pattern includes confidence metrics for reliability assessment |

---

## 🏗️ How It Works

### The Process

1. **Input**: Provide raw HTML and describe your extraction goal
2. **Preprocessing**: Clean and optimize HTML for analysis
3. **Chunking**: Split DOM into manageable pieces with context preservation
4. **Iterative Analysis**: Process each chunk with Claude, updating pattern memory
5. **Schema Generation**: Convert discovered patterns into robust CSS/XPath selectors
6. **Output**: Get a complete extraction plan ready for production use

---

## 📦 Installation

```bash
pip install ai-crawling-strategist
```

### Requirements
- Python 3.12+
- AWS account with Bedrock access (for Claude Sonnet 3.5)
- AWS credentials configured

---

## 🚀 Quick Start

### Basic Usage

```python
from ai_crawling_strategist import DOMStrategist

# Initialize with AWS credentials
strategist = DOMStrategist(
    aws_profile="default",  # or use aws_access_key_id/aws_secret_access_key
    aws_region="us-east-1"
)

# Analyze a webpage and generate extraction strategy
html_content = """<your webpage HTML here>"""
query = "extract all product listings with title, price, and rating"

schema = strategist.analyze(html_content, query)

# Use the generated schema with crawl4ai
print("Container:", schema.container_selector.selector)
print("Item selector:", schema.item_selector.selector)
print("Fields:", {name: field.primary_selector for name, field in schema.fields.items()})
```

### Global Configuration

```python
import ai_crawling_strategist as acs

# Set global AWS credentials
acs.aws_access_key_id = "your-access-key"
acs.aws_secret_access_key = "your-secret-key"
acs.aws_region = "us-east-1"

# Now use without explicit credentials
strategist = DOMStrategist()
```

### Advanced Configuration

```python
strategist = DOMStrategist(
    chunk_size=3000,           # Larger chunks for complex pages
    confidence_threshold=0.9,   # Higher confidence requirement
    enable_validation=True      # Validate selectors against source HTML
)
```

---

## 🎯 Use Cases (Examples)

### E-commerce Product Extraction
```python
query = "extract product name, price, rating, and availability status"
# → Generates selectors for product catalogs, search results, category pages
```

### Job Listing Analysis
```python
query = "extract job title, company, location, salary, and job description"
# → Discovers patterns in job boards, career pages, company listings
```

### News Article Processing
```python
query = "extract article headline, author, publication date, and content"
# → Identifies article structure across different news site layouts
```

### Real Estate Listings
```python
query = "extract property address, price, bedrooms, bathrooms, and square footage"
# → Handles various real estate site formats and listing structures
```

---

## 🏛️ Architecture

### Core Components

- **`DOMStrategist`**: Main orchestrator and user-facing API
- **`DOMChunker`**: Intelligent HTML chunking with boundary respect
- **`MemoryManager`**: Rolling memory evolution and pattern consolidation
- **`SchemaGenerator`**: Final extraction schema generation
- **`ClaudeClient`**: AWS Bedrock integration for LLM analysis

### Key Innovations

1. **Structure-Aware Chunking**: Never breaks HTML mid-tag, preserves parent-child relationships
2. **Confidence-Based Pattern Evolution**: Patterns gain or lose confidence as more evidence is discovered
3. **Memory Compression**: Automatically consolidates and prunes patterns to prevent token overflow
4. **Context Preservation**: Maintains DOM position and nesting information across chunks

---

## 🔑 AWS Configuration

### Option 1: AWS Profile
```bash
aws configure --profile myprofile
```

```python
strategist = DOMStrategist(aws_profile="myprofile")
```

### Option 2: Direct Credentials
```python
strategist = DOMStrategist(
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    aws_region="us-east-1"
)
```

### Option 3: Environment Variables
```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"
```

## 📋 Requirements

- **Python**: 3.12+
- **AWS Account**: With Bedrock access for Claude Sonnet 3.5
- **Dependencies**: BeautifulSoup4, boto3, pydantic, and others (see `pyproject.toml`)

---

## 🙏 Acknowledgments

- Built on AWS Bedrock and Claude Sonnet 3.5
- Designed for seamless integration with `crawl4ai`
- Inspired by the need for intelligent, adaptive web scraping solutions

---

*Transform any webpage into structured data with the power of AI-driven pattern discovery.*