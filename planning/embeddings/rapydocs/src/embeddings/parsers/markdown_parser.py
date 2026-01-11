"""
markdown_parser.py - Parser for Markdown documents

Dependencies:
    pip install markdown2 python-frontmatter mistune
"""

import re
from typing import List, Optional, Dict, Any
from pathlib import Path

from .base_parser import BaseParser, ParseResult, ParsedFile, CodeBlock, Language
from ...utils.common import check_optional_dependency

# Check optional dependencies
FRONTMATTER_AVAILABLE = check_optional_dependency('frontmatter', 'pip install python-frontmatter')
MARKDOWN2_AVAILABLE = check_optional_dependency('markdown2', 'pip install markdown2') 
MISTUNE_AVAILABLE = check_optional_dependency('mistune', 'pip install mistune')

# Import if available
if FRONTMATTER_AVAILABLE:
    import frontmatter
if MARKDOWN2_AVAILABLE:
    import markdown2
if MISTUNE_AVAILABLE:
    import mistune


class MarkdownParser(BaseParser):
    """Parser for Markdown documents with support for code blocks, headers, and frontmatter"""
    
    def __init__(self):
        super().__init__()
        self.markdown_extensions = {'.md', '.markdown', '.mdown', '.mkd', '.mdwn', '.mkdn', '.mdtxt', '.mdtext'}
        self.markdown_indicators = [
            '# ', '## ', '### ', '```', '---', '***', '___',
            '- [ ]', '- [x]', '* ', '1. ', '> ', '![', '][', 
            '**', '__', '*', '_', '`'
        ]
    
    def can_parse(self, filepath: str, content: str) -> bool:
        """Check if this parser can handle the given file"""
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() in self.markdown_extensions:
            return True
        
        # Check for README files
        if path.stem.upper() == 'README':
            return True
        
        # Check for markdown patterns
        lines = content.splitlines()[:50]  # Check first 50 lines
        markdown_score = 0
        
        for line in lines:
            # Headers
            if re.match(r'^#{1,6}\s+\S', line):
                markdown_score += 3
            # Code blocks
            elif line.strip().startswith('```'):
                markdown_score += 5
            # Lists
            elif re.match(r'^[\s]*[-*+]\s+\S', line) or re.match(r'^[\s]*\d+\.\s+\S', line):
                markdown_score += 2
            # Blockquotes
            elif line.strip().startswith('>'):
                markdown_score += 2
            # Links/Images
            elif '[' in line and '](' in line:
                markdown_score += 2
            # Horizontal rules
            elif re.match(r'^(---+|___+|\*\*\*+)\s*$', line):
                markdown_score += 2
        
        # If we find multiple markdown indicators, likely markdown
        return markdown_score >= 10
    
    def parse(self, content: str, filepath: str) -> ParseResult:
        """Parse Markdown content"""
        # Sanitize input
        sanitized = self.sanitize_input(content)
        if not sanitized.success:
            return sanitized
        
        content = sanitized.data
        parsed_file = ParsedFile.empty(filepath, Language.UNKNOWN)
        parsed_file.language = Language.UNKNOWN  # We'll set this to a markdown language if added to enum
        
        try:
            # Parse frontmatter if available
            metadata = {}
            frontmatter_content = None
            main_content = content
            
            if FRONTMATTER_AVAILABLE:
                try:
                    post = frontmatter.loads(content)
                    metadata = post.metadata
                    main_content = post.content
                    frontmatter_content = post.metadata
                except Exception as e:
                    self.logger.debug(f"Frontmatter parsing failed: {e}")
            
            # Store frontmatter as a block if present
            if frontmatter_content:
                parsed_file.blocks.append(CodeBlock(
                    type="frontmatter",
                    name="frontmatter",
                    content=str(frontmatter_content),
                    start_line=1,
                    end_line=content[:content.find('---', 3)].count('\n') if '---' in content else 1,
                    language="yaml",
                    metadata={"data": frontmatter_content}
                ))
            
            # Parse headers to understand document structure
            self._parse_headers(main_content, parsed_file)
            
            # Parse code blocks
            self._parse_code_blocks(main_content, parsed_file, content)
            
            # Parse links and references
            self._parse_links(main_content, parsed_file)
            
            # Parse tables
            self._parse_tables(main_content, parsed_file)
            
            # Parse task lists
            self._parse_task_lists(main_content, parsed_file)
            
            # Parse footnotes
            self._parse_footnotes(main_content, parsed_file)
            
            # Extract document metadata
            parsed_file.metadata = {
                "lines": len(content.splitlines()),
                "has_frontmatter": bool(frontmatter_content),
                "frontmatter": metadata,
                "has_toc": self._has_table_of_contents(main_content),
                "word_count": len(main_content.split()),
                "char_count": len(main_content),
                "reading_time_minutes": len(main_content.split()) // 200,  # Assuming 200 words per minute
                "markdown_features": self._detect_markdown_features(main_content)
            }
            
            # Detect if it's documentation
            if self._is_documentation(filepath, main_content, metadata):
                parsed_file.metadata["is_documentation"] = True
            
            return ParseResult(True, data=parsed_file)
            
        except Exception as e:
            error_msg = f"Error parsing markdown {filepath}: {str(e)}"
            self.logger.error(error_msg)
            parsed_file.parse_errors.append(error_msg)
            return ParseResult(True, data=parsed_file, warnings=[error_msg])
    
    def _parse_headers(self, content: str, parsed_file: ParsedFile):
        """Parse markdown headers to understand document structure"""
        lines = content.splitlines()
        header_stack = []  # Track header hierarchy
        
        for i, line in enumerate(lines):
            # ATX-style headers (# Header)
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                
                # Remove trailing #'s if present
                title = re.sub(r'\s*#+\s*$', '', title)
                
                # Create header block
                block = CodeBlock(
                    type="header",
                    name=title,
                    content=line,
                    signature=f"H{level}: {title}",
                    start_line=i + 1,
                    end_line=i + 1,
                    language="markdown",
                    metadata={
                        "level": level,
                        "text": title,
                        "anchor": self._create_anchor(title)
                    }
                )
                
                # Track hierarchy
                header_stack = [(lvl, name) for lvl, name in header_stack if lvl < level]
                header_stack.append((level, title))
                
                if header_stack[:-1]:
                    block.metadata["parent_headers"] = header_stack[:-1]
                
                parsed_file.blocks.append(block)
            
            # Setext-style headers (underlined with = or -)
            if i > 0:
                if re.match(r'^=+\s*$', line) and lines[i-1].strip():
                    # Level 1 header
                    title = lines[i-1].strip()
                    block = CodeBlock(
                        type="header",
                        name=title,
                        content=f"{lines[i-1]}\n{line}",
                        signature=f"H1: {title}",
                        start_line=i,
                        end_line=i + 1,
                        language="markdown",
                        metadata={"level": 1, "text": title, "style": "setext"}
                    )
                    parsed_file.blocks.append(block)
                
                elif re.match(r'^-+\s*$', line) and lines[i-1].strip() and len(line) >= 3:
                    # Level 2 header (must be at least 3 dashes to distinguish from list)
                    title = lines[i-1].strip()
                    block = CodeBlock(
                        type="header",
                        name=title,
                        content=f"{lines[i-1]}\n{line}",
                        signature=f"H2: {title}",
                        start_line=i,
                        end_line=i + 1,
                        language="markdown",
                        metadata={"level": 2, "text": title, "style": "setext"}
                    )
                    parsed_file.blocks.append(block)
    
    def _parse_code_blocks(self, content: str, parsed_file: ParsedFile, original_content: str):
        """Parse code blocks (both fenced and indented)"""
        
        # Parse fenced code blocks
        fenced_pattern = r'```(\w*)\n(.*?)```'
        for match in re.finditer(fenced_pattern, original_content, re.DOTALL):
            language = match.group(1) or 'plaintext'
            code = match.group(2)
            start_pos = match.start()
            end_pos = match.end()
            
            start_line = original_content[:start_pos].count('\n') + 1
            end_line = original_content[:end_pos].count('\n') + 1
            
            block = CodeBlock(
                type="code_block",
                name=f"code_block_{language}_{start_line}",
                content=code,
                signature=f"```{language}",
                start_line=start_line,
                end_line=end_line,
                language=language,
                metadata={
                    "fence_type": "backticks",
                    "original_language": language,
                    "lines_of_code": code.count('\n') + 1
                }
            )
            
            # Try to extract a name from comments or first line
            first_line = code.split('\n')[0] if code else ''
            if language in ['python', 'py'] and first_line.startswith('#'):
                block.metadata["comment"] = first_line[1:].strip()
            elif language in ['javascript', 'js', 'typescript', 'ts'] and first_line.startswith('//'):
                block.metadata["comment"] = first_line[2:].strip()
            
            parsed_file.blocks.append(block)
        
        # Parse inline code
        inline_pattern = r'`([^`]+)`'
        inline_codes = re.findall(inline_pattern, content)
        if inline_codes:
            parsed_file.metadata["inline_code_snippets"] = len(inline_codes)
            
            # Store unique inline code snippets
            unique_snippets = list(set(inline_codes))
            if len(unique_snippets) <= 20:  # Don't store too many
                parsed_file.metadata["unique_inline_codes"] = unique_snippets
    
    def _parse_links(self, content: str, parsed_file: ParsedFile):
        """Parse links and references"""
        links = []
        images = []
        references = {}
        
        # Inline links: [text](url)
        inline_link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        for match in re.finditer(inline_link_pattern, content):
            text = match.group(1)
            url = match.group(2)
            links.append({"text": text, "url": url, "type": "inline"})
        
        # Reference links: [text][ref]
        ref_link_pattern = r'\[([^\]]+)\]\[([^\]]*)\]'
        for match in re.finditer(ref_link_pattern, content):
            text = match.group(1)
            ref = match.group(2) or text  # Empty ref means use text as ref
            links.append({"text": text, "ref": ref, "type": "reference"})
        
        # Link definitions: [ref]: url
        link_def_pattern = r'^\[([^\]]+)\]:\s*(.+)$'
        for match in re.finditer(link_def_pattern, content, re.MULTILINE):
            ref = match.group(1)
            url = match.group(2)
            references[ref] = url
        
        # Images: ![alt](url)
        image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
        for match in re.finditer(image_pattern, content):
            alt = match.group(1)
            url = match.group(2)
            images.append({"alt": alt, "url": url})
        
        # Store in metadata
        if links:
            parsed_file.metadata["links"] = links
            parsed_file.metadata["link_count"] = len(links)
        
        if images:
            parsed_file.metadata["images"] = images
            parsed_file.metadata["image_count"] = len(images)
        
        if references:
            parsed_file.metadata["link_references"] = references
    
    def _parse_tables(self, content: str, parsed_file: ParsedFile):
        """Parse markdown tables"""
        lines = content.splitlines()
        tables = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check for table separator line
            if re.match(r'^[\s]*\|?[\s]*:?-+:?[\s]*\|', line):
                # Might be a table, check line before
                if i > 0 and '|' in lines[i-1]:
                    # Found a table
                    start_line = i - 1
                    headers = [cell.strip() for cell in lines[i-1].split('|') if cell.strip()]
                    
                    # Parse alignment
                    alignment = []
                    for cell in line.split('|'):
                        cell = cell.strip()
                        if cell.startswith(':') and cell.endswith(':'):
                            alignment.append('center')
                        elif cell.endswith(':'):
                            alignment.append('right')
                        else:
                            alignment.append('left')
                    
                    # Parse rows
                    rows = []
                    j = i + 1
                    while j < len(lines) and '|' in lines[j]:
                        row = [cell.strip() for cell in lines[j].split('|') if cell.strip()]
                        if row:
                            rows.append(row)
                        j += 1
                    
                    end_line = j - 1
                    
                    # Create table block
                    table_content = '\n'.join(lines[start_line:end_line + 1])
                    block = CodeBlock(
                        type="table",
                        name=f"table_{start_line}",
                        content=table_content,
                        signature=f"Table: {', '.join(headers[:3])}...",
                        start_line=start_line + 1,
                        end_line=end_line + 1,
                        language="markdown",
                        metadata={
                            "headers": headers,
                            "alignment": alignment,
                            "row_count": len(rows),
                            "column_count": len(headers)
                        }
                    )
                    parsed_file.blocks.append(block)
                    tables.append(block)
                    
                    i = j
                    continue
            
            i += 1
        
        if tables:
            parsed_file.metadata["table_count"] = len(tables)
    
    def _parse_task_lists(self, content: str, parsed_file: ParsedFile):
        """Parse task lists (checkboxes)"""
        tasks = []
        
        # Task list items
        task_pattern = r'^[\s]*[-*+]\s+\[([ xX])\]\s+(.+)$'
        
        for match in re.finditer(task_pattern, content, re.MULTILINE):
            checked = match.group(1).lower() == 'x'
            task_text = match.group(2)
            tasks.append({
                "text": task_text,
                "checked": checked,
                "line": content[:match.start()].count('\n') + 1
            })
        
        if tasks:
            parsed_file.metadata["tasks"] = tasks
            parsed_file.metadata["task_count"] = len(tasks)
            parsed_file.metadata["completed_tasks"] = sum(1 for t in tasks if t["checked"])
            parsed_file.metadata["pending_tasks"] = sum(1 for t in tasks if not t["checked"])
    
    def _parse_footnotes(self, content: str, parsed_file: ParsedFile):
        """Parse footnotes"""
        footnotes = {}
        
        # Footnote definitions: [^note]: Text
        footnote_def_pattern = r'^\[\^([^\]]+)\]:\s*(.+)$'
        for match in re.finditer(footnote_def_pattern, content, re.MULTILINE):
            note_id = match.group(1)
            note_text = match.group(2)
            footnotes[note_id] = note_text
        
        # Footnote references: [^note]
        footnote_ref_pattern = r'\[\^([^\]]+)\]'
        references = re.findall(footnote_ref_pattern, content)
        
        if footnotes:
            parsed_file.metadata["footnotes"] = footnotes
            parsed_file.metadata["footnote_references"] = references
    
    def _create_anchor(self, text: str) -> str:
        """Create an anchor ID from header text (GitHub-style)"""
        # Convert to lowercase
        anchor = text.lower()
        # Replace spaces with hyphens
        anchor = re.sub(r'\s+', '-', anchor)
        # Remove invalid characters
        anchor = re.sub(r'[^\w\-]', '', anchor)
        # Remove duplicate hyphens
        anchor = re.sub(r'-+', '-', anchor)
        # Strip leading/trailing hyphens
        anchor = anchor.strip('-')
        return anchor
    
    def _has_table_of_contents(self, content: str) -> bool:
        """Check if document has a table of contents"""
        toc_indicators = [
            'table of contents',
            'toc',
            '## contents',
            '## index',
            '[[_toc_]]',  # GitLab
            '[toc]',  # Some markdown processors
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in toc_indicators)
    
    def _detect_markdown_features(self, content: str) -> List[str]:
        """Detect which markdown features are used"""
        features = []
        
        # Check for various features
        if '```' in content or '~~~' in content:
            features.append('fenced_code_blocks')
        if re.search(r'^\s{4,}\S', content, re.MULTILINE):
            features.append('indented_code_blocks')
        if '|' in content and re.search(r'\|.*\|', content):
            features.append('tables')
        if re.search(r'!\[.*\]\(.*\)', content):
            features.append('images')
        if re.search(r'\[.*\]\(.*\)', content):
            features.append('links')
        if re.search(r'^\s*[-*+]\s+\[[ xX]\]', content, re.MULTILINE):
            features.append('task_lists')
        if re.search(r'^\s*>', content, re.MULTILINE):
            features.append('blockquotes')
        if re.search(r'\[\^[^\]]+\]', content):
            features.append('footnotes')
        if '$' in content or re.search(r'\$[^$]+\$', content):
            features.append('math')
        if re.search(r'^(---+|___+|\*\*\*+)\s*$', content, re.MULTILINE):
            features.append('horizontal_rules')
        if '**' in content or '__' in content:
            features.append('bold')
        if '*' in content or '_' in content:
            features.append('italic')
        if '~~' in content:
            features.append('strikethrough')
        if re.search(r'^\s*[-*+]\s+', content, re.MULTILINE):
            features.append('unordered_lists')
        if re.search(r'^\s*\d+\.\s+', content, re.MULTILINE):
            features.append('ordered_lists')
        if '<details>' in content or '<summary>' in content:
            features.append('html_details')
        if re.search(r'<[^>]+>', content):
            features.append('inline_html')
        
        return features
    
    def _is_documentation(self, filepath: str, content: str, metadata: Dict) -> bool:
        """Determine if this is documentation"""
        path = Path(filepath)
        
        # Check filename
        doc_filenames = ['readme', 'changelog', 'contributing', 'license', 'authors', 
                        'install', 'guide', 'tutorial', 'docs', 'api', 'reference']
        if any(name in path.stem.lower() for name in doc_filenames):
            return True
        
        # Check if in docs directory
        if 'docs' in path.parts or 'documentation' in path.parts:
            return True
        
        # Check frontmatter
        if metadata:
            if metadata.get('layout') in ['docs', 'documentation', 'api', 'guide']:
                return True
            if metadata.get('type') in ['docs', 'documentation', 'tutorial']:
                return True
        
        # Check content indicators
        doc_indicators = [
            '## installation',
            '## usage',
            '## api',
            '## getting started',
            '## configuration',
            '## examples',
            '## prerequisites',
            '## requirements'
        ]
        
        content_lower = content.lower()
        return sum(1 for indicator in doc_indicators if indicator in content_lower) >= 2