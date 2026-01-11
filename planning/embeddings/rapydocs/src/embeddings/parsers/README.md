# File Parsers

This directory contains language-specific parsers for extracting structured information from source code and document files.

## Available Parsers

### Python Parser (`python_parser.py`)
- **Method**: AST-based parsing using Python's built-in `ast` module
- **Accuracy**: High - uses official Python AST
- **Features**: Extracts functions, classes, methods, docstrings, type hints, decorators
- **Status**: Production-ready

### JavaScript/TypeScript Parser (`javascript_parser.py`)
- **Method**: Regular expression pattern matching
- **Accuracy**: Medium - regex-based heuristics
- **Limitations**: 
  - May struggle with complex ES6+ syntax
  - Limited TypeScript type extraction
  - JSX/TSX support is basic
- **Recommended Alternative**: For production use, consider implementing with tree-sitter
  ```bash
  pip install tree-sitter tree-sitter-javascript tree-sitter-typescript
  ```
- **Status**: Suitable for prototyping; upgrade recommended for production

### Markdown Parser (`markdown_parser.py`)
- **Method**: Multi-library approach (markdown, markdown2, mistune)
- **Features**: Frontmatter, headers, code blocks, tables, task lists, links
- **Status**: Production-ready

### HTML Parser (`html_parser.py`)
- **Method**: BeautifulSoup4 with lxml/html5lib
- **Features**: Framework detection (React, Vue, Angular), semantic element analysis
- **Status**: Production-ready

### JSON Parser (`json_parser.py`)
- **Method**: Native JSON parsing with semantic analysis
- **Features**: Pattern recognition, semantic type inference, field grouping
- **Status**: Production-ready

## Adding New Parsers

To add a new language parser:

1. Extend the `BaseParser` class
2. Implement required methods:
   - `can_parse(filepath, content)`: Determine if file can be parsed
   - `parse(content, filepath)`: Extract structured information
3. Register the parser in `FileProcessor` class

## Parser Selection Strategy

The `FileProcessor` automatically selects appropriate parsers based on:
1. File extension
2. MIME type
3. Content heuristics (shebang, language indicators)

## Performance Considerations

- **AST-based parsers** (Python): More accurate but slower
- **Regex-based parsers** (JavaScript): Faster but less accurate
- **Library-based parsers** (Markdown, HTML): Balance of speed and accuracy

## Future Improvements

1. **JavaScript/TypeScript**: Migrate to tree-sitter for accurate AST parsing
2. **Additional Languages**: Add parsers for:
   - Rust (using tree-sitter-rust)
   - Go (using tree-sitter-go)
   - Java (using tree-sitter-java)
   - C/C++ (using tree-sitter-c/cpp)
3. **Universal Fallback**: Implement tree-sitter universal parser for unsupported languages