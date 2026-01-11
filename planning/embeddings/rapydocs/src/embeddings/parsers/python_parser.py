"""
python_parser.py - Python language parser using AST
"""

import ast
import re
from typing import List, Optional
from pathlib import Path

from .base_parser import BaseParser, ParseResult, ParsedFile, CodeBlock, Language


class PythonParser(BaseParser):
    """Parser for Python source files using AST"""
    
    def __init__(self):
        super().__init__()
        self.python_extensions = {'.py', '.pyw', '.pyi'}
        self.python_indicators = [
            'def ', 'class ', 'import ', 'from ', 'if __name__',
            'async def', '@', 'self.', 'print(', '__init__'
        ]
    
    def can_parse(self, filepath: str, content: str) -> bool:
        """Check if this parser can handle the given file"""
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() in self.python_extensions:
            return True
        
        # Check shebang
        lines = content.splitlines()
        if lines and ('python' in lines[0].lower() or 'python3' in lines[0].lower()):
            return True
        
        # Check for Python-specific patterns
        sample = content[:1000]  # Check first 1000 chars
        python_score = sum(1 for indicator in self.python_indicators if indicator in sample)
        
        # If we find multiple Python indicators, likely Python
        return python_score >= 3
    
    def parse(self, content: str, filepath: str) -> ParseResult:
        """Parse Python code using AST"""
        # Sanitize input
        sanitized = self.sanitize_input(content)
        if not sanitized.success:
            return sanitized
        
        content = sanitized.data
        parsed_file = ParsedFile.empty(filepath, Language.PYTHON)
        
        try:
            tree = ast.parse(content)
            
            # First pass: collect module-level elements
            for node in tree.body:
                try:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        block = self._parse_function(node, content)
                        parsed_file.blocks.append(block)
                        if not node.name.startswith('_'):
                            parsed_file.exports.append(node.name)
                    
                    elif isinstance(node, ast.ClassDef):
                        class_blocks = self._parse_class(node, content)
                        parsed_file.blocks.extend(class_blocks)
                        if not node.name.startswith('_'):
                            parsed_file.exports.append(node.name)
                    
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            parsed_file.imports.append(alias.name)
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            parsed_file.imports.append(node.module)
                            # Also track what's imported from the module
                            for alias in node.names:
                                if alias.name != '*':
                                    parsed_file.imports.append(f"{node.module}.{alias.name}")
                    
                    elif isinstance(node, ast.Assign):
                        # Track module-level variables
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                parsed_file.global_vars.append(target.id)
                                # Check if it's an export (ALL_CAPS or specific patterns)
                                if target.id.isupper() or not target.id.startswith('_'):
                                    parsed_file.exports.append(target.id)
                
                except Exception as e:
                    error_msg = f"Error parsing node {type(node).__name__}: {str(e)}"
                    self.logger.warning(error_msg)
                    parsed_file.parse_errors.append(error_msg)
            
            # Add metadata
            parsed_file.metadata = {
                "lines": len(content.splitlines()),
                "has_main": self._has_main_block(content),
                "is_test_file": self._is_test_file(filepath, content),
                "encoding": self._detect_encoding(content)
            }
            
            return ParseResult(True, data=parsed_file)
            
        except SyntaxError as e:
            error_msg = f"Syntax error in {filepath}: Line {e.lineno}, {e.msg}"
            self.logger.error(error_msg)
            
            # Try to return partial results even on syntax error
            parsed_file.parse_errors.append(error_msg)
            parsed_file.metadata["syntax_error"] = True
            parsed_file.metadata["error_line"] = e.lineno
            
            # Try to parse what we can with regex fallback
            self._fallback_parse(content, parsed_file)
            
            return ParseResult(True, data=parsed_file, warnings=[error_msg])
        
        except Exception as e:
            error_msg = f"Unexpected error parsing {filepath}: {str(e)}"
            self.logger.error(error_msg)
            return ParseResult(False, error=error_msg)
    
    def _parse_function(self, node: ast.FunctionDef, source: str) -> CodeBlock:
        """Extract function information"""
        docstring = ast.get_docstring(node)
        
        # Build function signature
        args = []
        defaults = node.args.defaults
        
        # Regular arguments
        for i, arg in enumerate(node.args.args):
            arg_str = arg.arg
            
            # Add type annotation if present
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except Exception:
                    pass
            
            # Add default value if present
            default_offset = len(node.args.args) - len(defaults)
            if i >= default_offset:
                default_idx = i - default_offset
                try:
                    arg_str += f" = {ast.unparse(defaults[default_idx])}"
                except Exception:
                    arg_str += " = ..."
            
            args.append(arg_str)
        
        # Add *args and **kwargs
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        
        signature = f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {node.name}({', '.join(args)})"
        
        # Add return type if present
        if node.returns:
            try:
                signature += f" -> {ast.unparse(node.returns)}"
            except Exception:
                signature += " -> ..."
        
        # Get source lines
        lines = source.splitlines()
        start_line = node.lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 10
        content = '\n'.join(lines[start_line:end_line])
        
        # Detect decorators
        decorators = []
        for decorator in node.decorator_list:
            try:
                decorators.append(ast.unparse(decorator))
            except Exception:
                decorators.append("@...")
        
        block = CodeBlock(
            type="function",
            name=node.name,
            content=content,
            docstring=docstring,
            signature=signature,
            start_line=node.lineno,
            end_line=end_line,
            language="python"
        )
        
        if decorators:
            block.metadata["decorators"] = decorators
        
        return block
    
    def _parse_class(self, node: ast.ClassDef, source: str) -> List[CodeBlock]:
        """Extract class and method information"""
        blocks = []
        
        # Parse class itself
        docstring = ast.get_docstring(node)
        
        # Build class signature with bases
        bases = []
        for base in node.bases:
            try:
                bases.append(ast.unparse(base))
            except Exception:
                bases.append("...")
        
        signature = f"class {node.name}"
        if bases:
            signature += f"({', '.join(bases)})"
        
        lines = source.splitlines()
        start_line = node.lineno - 1
        
        # Find class definition end (just the class line and docstring)
        class_def_lines = []
        indent_level = len(lines[start_line]) - len(lines[start_line].lstrip())
        
        for i in range(start_line, min(start_line + 10, len(lines))):
            line = lines[i]
            if i > start_line and line.strip() and not line[indent_level:].startswith(' '):
                break
            class_def_lines.append(line)
            if ':' in line and i > start_line:
                break
        
        # Get decorators
        decorators = []
        for decorator in node.decorator_list:
            try:
                decorators.append(ast.unparse(decorator))
            except Exception:
                decorators.append("@...")
        
        class_block = CodeBlock(
            type="class",
            name=node.name,
            content='\n'.join(class_def_lines),
            docstring=docstring,
            signature=signature,
            start_line=node.lineno,
            end_line=node.lineno + len(class_def_lines),
            language="python"
        )
        
        if decorators:
            class_block.metadata["decorators"] = decorators
        
        # Check for dataclass, enum, etc.
        if any('@dataclass' in d for d in decorators):
            class_block.metadata["is_dataclass"] = True
        
        # Count methods and properties
        method_count = 0
        property_count = 0
        
        blocks.append(class_block)
        
        # Parse methods and nested classes
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_block = self._parse_function(item, source)
                method_block.type = "method"
                method_block.metadata["class"] = node.name
                
                # Check if it's a property
                if any(d in ['@property', '@cached_property'] for d in method_block.metadata.get("decorators", [])):
                    method_block.type = "property"
                    property_count += 1
                else:
                    method_count += 1
                
                # Check for special methods
                if item.name.startswith('__') and item.name.endswith('__'):
                    method_block.metadata["is_magic_method"] = True
                
                blocks.append(method_block)
            
            elif isinstance(item, ast.ClassDef):
                # Nested class
                nested_blocks = self._parse_class(item, source)
                for block in nested_blocks:
                    block.metadata["parent_class"] = node.name
                blocks.extend(nested_blocks)
        
        # Update class metadata
        class_block.metadata["method_count"] = method_count
        class_block.metadata["property_count"] = property_count
        
        return blocks
    
    def _fallback_parse(self, content: str, parsed_file: ParsedFile):
        """Fallback regex-based parsing for files with syntax errors"""
        # Try to extract functions
        func_pattern = r'^(async\s+)?def\s+(\w+)\s*\([^)]*\):'
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            name = match.group(2)
            start = content[:match.start()].count('\n') + 1
            
            parsed_file.blocks.append(CodeBlock(
                type="function",
                name=name,
                content=f"# Function {name} (extracted via fallback)",
                start_line=start,
                end_line=start,
                language="python",
                metadata={"fallback_extracted": True}
            ))
        
        # Try to extract classes
        class_pattern = r'^class\s+(\w+)(?:\([^)]*\))?:'
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            name = match.group(1)
            start = content[:match.start()].count('\n') + 1
            
            parsed_file.blocks.append(CodeBlock(
                type="class",
                name=name,
                content=f"# Class {name} (extracted via fallback)",
                start_line=start,
                end_line=start,
                language="python",
                metadata={"fallback_extracted": True}
            ))
        
        # Extract imports
        import_pattern = r'^(?:from\s+(\S+)\s+)?import\s+(.+)$'
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            if match.group(1):
                parsed_file.imports.append(match.group(1))
            else:
                imports = match.group(2).split(',')
                parsed_file.imports.extend([imp.strip() for imp in imports])
    
    def _has_main_block(self, content: str) -> bool:
        """Check if file has if __name__ == '__main__' block"""
        return 'if __name__ == "__main__"' in content or "if __name__ == '__main__'" in content
    
    def _is_test_file(self, filepath: str, content: str) -> bool:
        """Check if this appears to be a test file"""
        path = Path(filepath)
        
        # Check filename
        if 'test' in path.stem.lower() or path.stem.startswith('test_'):
            return True
        
        # Check for test frameworks
        test_indicators = ['import unittest', 'import pytest', 'from unittest', 'from pytest']
        return any(indicator in content for indicator in test_indicators)
    
    def _detect_encoding(self, content: str) -> str:
        """Detect file encoding from coding declaration"""
        # Check first two lines for encoding declaration
        lines = content.splitlines()[:2]
        for line in lines:
            match = re.search(r'coding[=:]\s*([-\w.]+)', line)
            if match:
                return match.group(1)
        return 'utf-8'
