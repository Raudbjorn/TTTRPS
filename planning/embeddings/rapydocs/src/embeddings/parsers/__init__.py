"""
Parser modules for various file types
"""

from .base_parser import BaseParser, ParseResult, ParsedFile, Language, CodeBlock
from .python_parser import PythonParser
from .markdown_parser import MarkdownParser
from .html_parser import HTMLParser
from .json_parser import JSONParser

# Try to import tree-sitter based JavaScript parser, fallback to regex-based
try:
    from .javascript_tree_parser import JavaScriptTreeParser as JavaScriptParser
except ImportError:
    from .javascript_parser import JavaScriptParser

__all__ = [
    'BaseParser',
    'ParseResult',
    'ParsedFile',
    'Language', 
    'CodeBlock',
    'PythonParser',
    'JavaScriptParser',
    'MarkdownParser',
    'HTMLParser',
    'JSONParser'
]