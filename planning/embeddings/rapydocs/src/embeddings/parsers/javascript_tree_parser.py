"""
javascript_tree_parser.py - JavaScript and TypeScript parser using tree-sitter
"""

import re
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging

from .base_parser import BaseParser, ParseResult, ParsedFile, CodeBlock, Language

try:
    import tree_sitter_javascript as tsjson
    import tree_sitter_typescript as tsts
    from tree_sitter import Language as TSLanguage, Parser as TSParser, Node
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


class JavaScriptTreeParser(BaseParser):
    """Parser for JavaScript/TypeScript source files using tree-sitter.
    
    This parser provides accurate parsing using tree-sitter's concrete syntax tree,
    handling complex language features and nested structures correctly.
    Falls back to basic parsing if tree-sitter is not available.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.js_extensions = {'.js', '.jsx', '.mjs', '.cjs'}
        self.ts_extensions = {'.ts', '.tsx', '.d.ts'}
        self.all_extensions = self.js_extensions | self.ts_extensions
        
        self.js_parser = None
        self.ts_parser = None
        
        if TREE_SITTER_AVAILABLE:
            try:
                # Initialize JavaScript parser
                JS_LANGUAGE = TSLanguage(tsjson.language())
                self.js_parser = TSParser()
                self.js_parser.set_language(JS_LANGUAGE)
                
                # Initialize TypeScript parser  
                TS_LANGUAGE = TSLanguage(tsts.language_typescript())
                TSX_LANGUAGE = TSLanguage(tsts.language_tsx())
                self.ts_parser = TSParser()
                self.ts_parser.set_language(TS_LANGUAGE)
                
                # TSX parser for .tsx files
                self.tsx_parser = TSParser()
                self.tsx_parser.set_language(TSX_LANGUAGE)
                
                self.logger.info("Tree-sitter parsers initialized successfully")
            except Exception as e:
                self.logger.warning(f"Failed to initialize tree-sitter: {e}")
                self.js_parser = None
                self.ts_parser = None
        else:
            self.logger.info("Tree-sitter not available, will use fallback parsing")
    
    def can_parse(self, filepath: str, content: str) -> bool:
        """Check if this parser can handle the given file"""
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() in self.all_extensions:
            return True
        
        # Check shebang for node
        lines = content.splitlines()
        if lines and 'node' in lines[0].lower():
            return True
        
        # Check for JS/TS patterns
        js_indicators = ['function ', 'const ', 'let ', 'var ', '=>', 'class ', 'export ', 'import ']
        sample = content[:2000]
        js_score = sum(1 for indicator in js_indicators if indicator in sample)
        
        return js_score >= 3
    
    def parse(self, content: str, filepath: str) -> ParseResult:
        """Parse JavaScript/TypeScript code using tree-sitter"""
        # Sanitize input
        sanitized = self.sanitize_input(content)
        if not sanitized.success:
            return sanitized
        
        content = sanitized.data
        
        # Detect language variant
        language = self._detect_language(filepath, content)
        
        # Use tree-sitter if available
        if self.js_parser and self.ts_parser:
            return self._parse_with_tree_sitter(content, filepath, language)
        else:
            # Fallback to basic parsing
            return self._parse_fallback(content, filepath, language)
    
    def _detect_language(self, filepath: str, content: str) -> Language:
        """Detect whether this is JavaScript or TypeScript"""
        path = Path(filepath)
        
        if path.suffix.lower() in self.ts_extensions:
            return Language.TYPESCRIPT
        
        # Check for TypeScript-specific syntax
        ts_indicators = ['interface ', 'type ', 'enum ', ': string', ': number', ': boolean']
        ts_score = sum(1 for indicator in ts_indicators if indicator in content)
        if ts_score >= 2:
            return Language.TYPESCRIPT
        
        return Language.JAVASCRIPT
    
    def _parse_with_tree_sitter(self, content: str, filepath: str, language: Language) -> ParseResult:
        """Parse using tree-sitter for accurate AST parsing"""
        parsed_file = ParsedFile.empty(filepath, language)
        
        try:
            # Select appropriate parser
            path = Path(filepath)
            if path.suffix.lower() == '.tsx':
                parser = self.tsx_parser
            elif language == Language.TYPESCRIPT:
                parser = self.ts_parser
            else:
                parser = self.js_parser
            
            # Parse the content
            tree = parser.parse(bytes(content, "utf8"))
            root_node = tree.root_node
            
            # Extract various code elements
            self._extract_functions(root_node, content, parsed_file)
            self._extract_classes(root_node, content, parsed_file)
            self._extract_imports(root_node, content, parsed_file)
            self._extract_exports(root_node, content, parsed_file)
            
            if language == Language.TYPESCRIPT:
                self._extract_interfaces(root_node, content, parsed_file)
                self._extract_type_aliases(root_node, content, parsed_file)
                self._extract_enums(root_node, content, parsed_file)
            
            # Add metadata
            parsed_file.metadata = {
                "lines": len(content.splitlines()),
                "parse_errors": len([n for n in root_node.children if n.has_error]),
                "is_module": self._is_module(root_node),
                "is_react": self._is_react_component(content, parsed_file.imports),
                "is_test_file": self._is_test_file(filepath, content)
            }
            
            return ParseResult(True, data=parsed_file)
            
        except Exception as e:
            error_msg = f"Tree-sitter parsing error for {filepath}: {str(e)}"
            self.logger.error(error_msg)
            # Fallback to basic parsing
            return self._parse_fallback(content, filepath, language)
    
    def _extract_functions(self, node: 'Node', content: str, parsed_file: ParsedFile):
        """Extract function declarations using tree-sitter"""
        function_types = [
            'function_declaration',
            'function_expression', 
            'arrow_function',
            'method_definition',
            'generator_function_declaration'
        ]
        
        for child in node.children:
            if child.type in function_types:
                name = self._get_function_name(child, content)
                if name:
                    start_line = child.start_point[0] + 1
                    end_line = child.end_point[0] + 1
                    func_content = content[child.start_byte:child.end_byte]
                    
                    # Extract docstring/comments
                    docstring = self._extract_preceding_comment(child, content)
                    
                    # Extract signature
                    signature = self._extract_signature(child, content)
                    
                    block = CodeBlock(
                        type="function",
                        name=name,
                        content=func_content,
                        docstring=docstring,
                        signature=signature,
                        start_line=start_line,
                        end_line=end_line,
                        language=parsed_file.language.value,
                        metadata={
                            "is_async": self._is_async(child),
                            "is_generator": child.type == 'generator_function_declaration',
                            "is_exported": self._is_exported(child)
                        }
                    )
                    
                    parsed_file.blocks.append(block)
                    
                    if block.metadata.get("is_exported"):
                        parsed_file.exports.append(name)
            
            # Recurse for nested functions
            self._extract_functions(child, content, parsed_file)
    
    def _extract_classes(self, node: 'Node', content: str, parsed_file: ParsedFile):
        """Extract class declarations using tree-sitter"""
        if node.type == 'class_declaration' or node.type == 'class_expression':
            name = self._get_class_name(node, content)
            if name:
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                class_content = content[node.start_byte:node.end_byte]
                
                # Extract docstring/comments
                docstring = self._extract_preceding_comment(node, content)
                
                # Extract signature
                signature = self._extract_signature(node, content)
                
                # Extract inheritance info
                extends = None
                implements = []
                for child in node.children:
                    if child.type == 'class_heritage':
                        for heritage_child in child.children:
                            if heritage_child.type == 'extends_clause':
                                extends = content[heritage_child.start_byte:heritage_child.end_byte]
                            elif heritage_child.type == 'implements_clause':
                                implements.append(content[heritage_child.start_byte:heritage_child.end_byte])
                
                block = CodeBlock(
                    type="class",
                    name=name,
                    content=class_content,
                    docstring=docstring,
                    signature=signature,
                    start_line=start_line,
                    end_line=end_line,
                    language=parsed_file.language.value,
                    metadata={
                        "is_exported": self._is_exported(node),
                        "extends": extends,
                        "implements": implements
                    }
                )
                
                parsed_file.blocks.append(block)
                
                if block.metadata.get("is_exported"):
                    parsed_file.exports.append(name)
                
                # Extract class methods
                self._extract_class_methods(node, content, name, parsed_file)
        
        # Recurse for nested classes
        for child in node.children:
            if child.type not in ['class_declaration', 'class_expression']:
                self._extract_classes(child, content, parsed_file)
    
    def _extract_class_methods(self, class_node: 'Node', content: str, class_name: str, parsed_file: ParsedFile):
        """Extract methods from a class"""
        for child in class_node.children:
            if child.type == 'class_body':
                for body_child in child.children:
                    if body_child.type == 'method_definition':
                        method_name = self._get_method_name(body_child, content)
                        if method_name and method_name != 'constructor':
                            start_line = body_child.start_point[0] + 1
                            end_line = body_child.end_point[0] + 1
                            
                            block = CodeBlock(
                                type="method",
                                name=method_name,
                                content=content[body_child.start_byte:body_child.end_byte],
                                signature=self._extract_signature(body_child, content),
                                start_line=start_line,
                                end_line=end_line,
                                language=parsed_file.language.value,
                                metadata={
                                    "class": class_name,
                                    "is_static": self._is_static(body_child),
                                    "is_async": self._is_async(body_child),
                                    "visibility": self._get_visibility(body_child)
                                }
                            )
                            
                            parsed_file.blocks.append(block)
    
    def _extract_interfaces(self, node: 'Node', content: str, parsed_file: ParsedFile):
        """Extract TypeScript interfaces"""
        if node.type == 'interface_declaration':
            name_node = self._find_child_by_type(node, 'type_identifier')
            if name_node:
                name = content[name_node.start_byte:name_node.end_byte]
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                
                block = CodeBlock(
                    type="interface",
                    name=name,
                    content=content[node.start_byte:node.end_byte],
                    signature=self._extract_signature(node, content),
                    start_line=start_line,
                    end_line=end_line,
                    language="typescript",
                    metadata={"is_exported": self._is_exported(node)}
                )
                
                parsed_file.blocks.append(block)
                
                if block.metadata.get("is_exported"):
                    parsed_file.exports.append(name)
        
        # Recurse
        for child in node.children:
            self._extract_interfaces(child, content, parsed_file)
    
    def _extract_type_aliases(self, node: 'Node', content: str, parsed_file: ParsedFile):
        """Extract TypeScript type aliases"""
        if node.type == 'type_alias_declaration':
            name_node = self._find_child_by_type(node, 'type_identifier')
            if name_node:
                name = content[name_node.start_byte:name_node.end_byte]
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                
                block = CodeBlock(
                    type="type_alias",
                    name=name,
                    content=content[node.start_byte:node.end_byte],
                    signature=f"type {name}",
                    start_line=start_line,
                    end_line=end_line,
                    language="typescript",
                    metadata={"is_exported": self._is_exported(node)}
                )
                
                parsed_file.blocks.append(block)
                
                if block.metadata.get("is_exported"):
                    parsed_file.exports.append(name)
        
        # Recurse
        for child in node.children:
            self._extract_type_aliases(child, content, parsed_file)
    
    def _extract_enums(self, node: 'Node', content: str, parsed_file: ParsedFile):
        """Extract TypeScript enums"""
        if node.type == 'enum_declaration':
            name_node = self._find_child_by_type(node, 'identifier')
            if name_node:
                name = content[name_node.start_byte:name_node.end_byte]
                start_line = node.start_point[0] + 1
                end_line = node.end_point[0] + 1
                
                block = CodeBlock(
                    type="enum",
                    name=name,
                    content=content[node.start_byte:node.end_byte],
                    signature=self._extract_signature(node, content),
                    start_line=start_line,
                    end_line=end_line,
                    language="typescript",
                    metadata={
                        "is_exported": self._is_exported(node),
                        "is_const": 'const' in content[node.start_byte:node.start_byte + 50]
                    }
                )
                
                parsed_file.blocks.append(block)
                
                if block.metadata.get("is_exported"):
                    parsed_file.exports.append(name)
        
        # Recurse
        for child in node.children:
            self._extract_enums(child, content, parsed_file)
    
    def _extract_imports(self, node: 'Node', content: str, parsed_file: ParsedFile):
        """Extract import statements"""
        if node.type == 'import_statement':
            # Extract module name from string node
            for child in node.children:
                if child.type == 'string':
                    module = content[child.start_byte + 1:child.end_byte - 1]  # Remove quotes
                    if module not in parsed_file.imports:
                        parsed_file.imports.append(module)
        
        # Also handle require() calls
        elif node.type == 'call_expression':
            if self._is_require_call(node, content):
                for child in node.children:
                    if child.type == 'arguments':
                        for arg_child in child.children:
                            if arg_child.type == 'string':
                                module = content[arg_child.start_byte + 1:arg_child.end_byte - 1]
                                if module not in parsed_file.imports:
                                    parsed_file.imports.append(module)
        
        # Recurse
        for child in node.children:
            self._extract_imports(child, content, parsed_file)
    
    def _extract_exports(self, node: 'Node', content: str, parsed_file: ParsedFile):
        """Extract export statements"""
        if node.type == 'export_statement':
            # Check what is being exported
            for child in node.children:
                if child.type in ['function_declaration', 'class_declaration', 'lexical_declaration']:
                    # Extract name from the declaration
                    name = self._get_declaration_name(child, content)
                    if name and name not in parsed_file.exports:
                        parsed_file.exports.append(name)
                elif child.type == 'export_clause':
                    # Named exports
                    for export_child in child.children:
                        if export_child.type == 'export_specifier':
                            name_node = self._find_child_by_type(export_child, 'identifier')
                            if name_node:
                                name = content[name_node.start_byte:name_node.end_byte]
                                if name not in parsed_file.exports:
                                    parsed_file.exports.append(name)
        
        # Recurse
        for child in node.children:
            self._extract_exports(child, content, parsed_file)
    
    # Helper methods
    def _find_child_by_type(self, node: 'Node', type_name: str) -> Optional['Node']:
        """Find first child node of given type"""
        for child in node.children:
            if child.type == type_name:
                return child
        return None
    
    def _get_function_name(self, node: 'Node', content: str) -> Optional[str]:
        """Extract function name from node"""
        # For regular function declarations
        name_node = self._find_child_by_type(node, 'identifier')
        if name_node:
            return content[name_node.start_byte:name_node.end_byte]
        
        # For variable declarations with arrow functions
        if node.parent and node.parent.type == 'variable_declarator':
            name_node = self._find_child_by_type(node.parent, 'identifier')
            if name_node:
                return content[name_node.start_byte:name_node.end_byte]
        
        return None
    
    def _get_class_name(self, node: 'Node', content: str) -> Optional[str]:
        """Extract class name from node"""
        name_node = self._find_child_by_type(node, 'identifier')
        if name_node:
            return content[name_node.start_byte:name_node.end_byte]
        return None
    
    def _get_method_name(self, node: 'Node', content: str) -> Optional[str]:
        """Extract method name from node"""
        name_node = self._find_child_by_type(node, 'property_identifier')
        if name_node:
            return content[name_node.start_byte:name_node.end_byte]
        return None
    
    def _get_declaration_name(self, node: 'Node', content: str) -> Optional[str]:
        """Extract name from various declaration types"""
        if node.type in ['function_declaration', 'class_declaration']:
            return self._get_function_name(node, content) or self._get_class_name(node, content)
        elif node.type == 'lexical_declaration':
            # For const/let/var declarations
            for child in node.children:
                if child.type == 'variable_declarator':
                    name_node = self._find_child_by_type(child, 'identifier')
                    if name_node:
                        return content[name_node.start_byte:name_node.end_byte]
        return None
    
    def _extract_signature(self, node: 'Node', content: str) -> str:
        """Extract clean signature from node"""
        # Get content up to the opening brace
        signature = content[node.start_byte:node.end_byte].split('{')[0].strip()
        # Clean up whitespace
        signature = re.sub(r'\s+', ' ', signature)
        return signature
    
    def _extract_preceding_comment(self, node: 'Node', content: str) -> Optional[str]:
        """Extract JSDoc or comment immediately preceding the node"""
        # Look for comment nodes immediately before this node
        if node.prev_sibling and node.prev_sibling.type == 'comment':
            comment = content[node.prev_sibling.start_byte:node.prev_sibling.end_byte]
            # Clean JSDoc comment
            if comment.startswith('/**'):
                lines = comment[3:-2].split('\n')
                cleaned = []
                for line in lines:
                    line = line.strip()
                    if line.startswith('*'):
                        line = line[1:].strip()
                    if line:
                        cleaned.append(line)
                return '\n'.join(cleaned) if cleaned else None
        return None
    
    def _is_async(self, node: 'Node') -> bool:
        """Check if function/method is async"""
        for child in node.children:
            if child.type == 'async':
                return True
        return False
    
    def _is_static(self, node: 'Node') -> bool:
        """Check if method is static"""
        for child in node.children:
            if child.type == 'static':
                return True
        return False
    
    def _is_exported(self, node: 'Node') -> bool:
        """Check if declaration is exported"""
        if node.parent and node.parent.type == 'export_statement':
            return True
        return False
    
    def _get_visibility(self, node: 'Node') -> str:
        """Get visibility modifier (public/private/protected)"""
        for child in node.children:
            if child.type in ['private', 'protected', 'public']:
                return child.type
        return 'public'
    
    def _is_require_call(self, node: 'Node', content: str) -> bool:
        """Check if node is a require() call"""
        if node.type == 'call_expression':
            func_node = self._find_child_by_type(node, 'identifier')
            if func_node:
                func_name = content[func_node.start_byte:func_node.end_byte]
                return func_name == 'require'
        return False
    
    def _is_module(self, root_node: 'Node') -> bool:
        """Check if file uses module syntax"""
        for child in root_node.children:
            if child.type in ['import_statement', 'export_statement']:
                return True
        return False
    
    def _is_react_component(self, content: str, imports: List[str]) -> bool:
        """Check if file contains React components"""
        # Check imports
        if any('react' in imp.lower() for imp in imports):
            return True
        # Check for JSX
        if re.search(r'<[A-Z]\w+', content):  # JSX component
            return True
        return False
    
    def _is_test_file(self, filepath: str, content: str) -> bool:
        """Check if this is a test file"""
        path = Path(filepath)
        
        # Check filename
        test_patterns = ['.test.', '.spec.', '__tests__', 'test_']
        if any(pattern in path.stem.lower() for pattern in test_patterns):
            return True
        
        # Check for test frameworks
        test_indicators = ['describe(', 'it(', 'test(', 'expect(']
        return any(indicator in content for indicator in test_indicators)
    
    def _parse_fallback(self, content: str, filepath: str, language: Language) -> ParseResult:
        """Fallback to basic regex-based parsing"""
        parsed_file = ParsedFile.empty(filepath, language)
        
        try:
            # Simple regex patterns for basic extraction
            # Extract functions
            func_pattern = r'(?:async\s+)?function\s+(\w+)\s*\([^)]*\)'
            for match in re.finditer(func_pattern, content):
                name = match.group(1)
                start_line = content[:match.start()].count('\n') + 1
                
                block = CodeBlock(
                    type="function",
                    name=name,
                    content=match.group(0),
                    signature=match.group(0),
                    start_line=start_line,
                    end_line=start_line,
                    language=language.value
                )
                parsed_file.blocks.append(block)
            
            # Extract classes
            class_pattern = r'class\s+(\w+)'
            for match in re.finditer(class_pattern, content):
                name = match.group(1)
                start_line = content[:match.start()].count('\n') + 1
                
                block = CodeBlock(
                    type="class",
                    name=name,
                    content=match.group(0),
                    signature=match.group(0),
                    start_line=start_line,
                    end_line=start_line,
                    language=language.value
                )
                parsed_file.blocks.append(block)
            
            # Extract imports
            import_pattern = r'(?:import.*from\s+[\'"]([^\'"]+)[\'"]|require\s*\([\'"]([^\'"]+)[\'"]\))'
            for match in re.finditer(import_pattern, content):
                module = match.group(1) or match.group(2)
                if module and module not in parsed_file.imports:
                    parsed_file.imports.append(module)
            
            # Basic metadata
            parsed_file.metadata = {
                "lines": len(content.splitlines()),
                "fallback_parsing": True
            }
            
            return ParseResult(True, data=parsed_file)
            
        except Exception as e:
            error_msg = f"Fallback parsing error for {filepath}: {str(e)}"
            self.logger.error(error_msg)
            parsed_file.parse_errors.append(error_msg)
            return ParseResult(True, data=parsed_file, warnings=[error_msg])