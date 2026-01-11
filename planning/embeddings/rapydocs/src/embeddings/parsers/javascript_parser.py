"""
javascript_parser.py - JavaScript and TypeScript parser using regex patterns
"""

import re
from typing import List, Optional, Tuple
from pathlib import Path

from .base_parser import BaseParser, ParseResult, ParsedFile, CodeBlock, Language


class JavaScriptParser(BaseParser):
    """Parser for JavaScript/TypeScript source files using regular expression patterns.
    
    This parser is suitable for simple files and quick prototyping, but may not handle
    complex language features or nested structures. For production use with complex
    JavaScript/TypeScript, consider using tree-sitter (available as optional dependency).
    
    See src/embeddings/parsers/README.md for detailed implementation notes and upgrade path.
    """
    
    def __init__(self):
        super().__init__()
        self.js_extensions = {'.js', '.jsx', '.mjs', '.cjs'}
        self.ts_extensions = {'.ts', '.tsx', '.d.ts'}
        self.all_extensions = self.js_extensions | self.ts_extensions
        
        # Patterns that indicate JavaScript/TypeScript
        self.js_indicators = [
            'function ', 'const ', 'let ', 'var ', '=>', 'class ',
            'export ', 'import ', 'require(', 'module.exports',
            'async ', 'await ', 'console.', 'document.', 'window.'
        ]
        
        self.ts_indicators = [
            'interface ', 'type ', 'enum ', ': string', ': number',
            ': boolean', '<T>', 'as ', 'implements ', 'namespace ',
            'declare ', 'readonly ', 'private ', 'public ', 'protected '
        ]
    
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
        
        # Score the content
        sample = content[:2000]
        js_score = sum(1 for indicator in self.js_indicators if indicator in sample)
        ts_score = sum(1 for indicator in self.ts_indicators if indicator in sample)
        
        # If we find multiple JS/TS indicators, likely JavaScript/TypeScript
        return (js_score + ts_score) >= 3
    
    def parse(self, content: str, filepath: str) -> ParseResult:
        """Parse JavaScript/TypeScript code using regex patterns"""
        # Sanitize input
        sanitized = self.sanitize_input(content)
        if not sanitized.success:
            return sanitized
        
        content = sanitized.data
        
        # Detect language variant
        language = self._detect_language(filepath, content)
        
        parsed_file = ParsedFile.empty(filepath, language)
        
        try:
            # Remove comments for cleaner parsing (but keep line numbers)
            content_no_comments = self._remove_comments(content)
            
            # Parse different elements
            self._parse_functions(content, content_no_comments, parsed_file)
            self._parse_classes(content, content_no_comments, parsed_file)
            self._parse_imports(content_no_comments, parsed_file)
            self._parse_exports(content_no_comments, parsed_file)
            self._parse_interfaces(content_no_comments, parsed_file)
            self._parse_type_aliases(content_no_comments, parsed_file)
            self._parse_enums(content_no_comments, parsed_file)
            self._parse_variables(content_no_comments, parsed_file)
            
            # Add metadata
            parsed_file.metadata = {
                "lines": len(content.splitlines()),
                "is_module": self._is_module(content),
                "is_react": self._is_react_component(content),
                "is_test_file": self._is_test_file(filepath, content),
                "framework": self._detect_framework(content, parsed_file.imports)
            }
            
            return ParseResult(True, data=parsed_file)
            
        except Exception as e:
            error_msg = f"Error parsing {filepath}: {str(e)}"
            self.logger.error(error_msg)
            
            # Return partial results
            parsed_file.parse_errors.append(error_msg)
            return ParseResult(True, data=parsed_file, warnings=[error_msg])
    
    def _detect_language(self, filepath: str, content: str) -> Language:
        """Detect whether this is JavaScript or TypeScript"""
        path = Path(filepath)
        
        if path.suffix.lower() in self.ts_extensions:
            return Language.TYPESCRIPT
        
        # Check for TypeScript-specific syntax
        ts_score = sum(1 for indicator in self.ts_indicators if indicator in content)
        if ts_score >= 2:
            return Language.TYPESCRIPT
        
        return Language.JAVASCRIPT
    
    def _remove_comments(self, content: str) -> str:
        """Remove comments while preserving line numbers"""
        # Remove single-line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        
        # Remove multi-line comments but keep newlines
        def replace_multiline(match):
            return '\n' * match.group(0).count('\n')
        
        content = re.sub(r'/\*.*?\*/', replace_multiline, content, flags=re.DOTALL)
        
        return content
    
    def _parse_functions(self, original: str, content: str, parsed_file: ParsedFile):
        """Parse function declarations and expressions"""
        patterns = [
            # Standard function declaration
            (r'(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*(?:<[^>]+>)?\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*{', 'function'),
            # Arrow function assigned to const/let/var
            (r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::\s*[^=]+)?\s*=\s*(?:async\s+)?\([^)]*\)(?:\s*:\s*[^=]+)?\s*=>', 'arrow'),
            # Arrow function with single parameter
            (r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::\s*[^=]+)?\s*=\s*(?:async\s+)?(\w+)(?:\s*:\s*[^=]+)?\s*=>', 'arrow'),
            # Function expression
            (r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*(?:\w+)?\s*\([^)]*\)\s*{', 'expression'),
            # Method-like function in object
            (r'(\w+)\s*:\s*(?:async\s+)?function\s*\([^)]*\)\s*{', 'method'),
            # Shorthand method in object
            (r'(?:async\s+)?(\w+)\s*\([^)]*\)\s*{', 'method'),
        ]
        
        for pattern, func_type in patterns:
            for match in re.finditer(pattern, content):
                name = match.group(1)
                if name and not self._is_keyword(name):
                    start_pos = match.start()
                    
                    # Find the end of the function
                    end_pos = self._find_block_end(content, start_pos)
                    
                    # Get the function content from original (with comments)
                    func_content = original[start_pos:end_pos] if end_pos > start_pos else match.group(0)
                    
                    # Extract signature
                    signature = self._extract_function_signature(match.group(0))
                    
                    # Extract JSDoc if present
                    docstring = self._extract_jsdoc(original, start_pos)
                    
                    # Calculate line numbers
                    start_line = original[:start_pos].count('\n') + 1
                    end_line = original[:end_pos].count('\n') + 1 if end_pos > start_pos else start_line
                    
                    block = CodeBlock(
                        type="function",
                        name=name,
                        content=func_content,
                        docstring=docstring,
                        signature=signature,
                        start_line=start_line,
                        end_line=end_line,
                        language=parsed_file.language.value,
                        metadata={"function_type": func_type}
                    )
                    
                    # Check if it's exported
                    if 'export' in match.group(0):
                        parsed_file.exports.append(name)
                        block.metadata["exported"] = True
                    
                    # Check if it's async
                    if 'async' in match.group(0):
                        block.metadata["is_async"] = True
                    
                    # Check if it's a generator
                    if 'function*' in match.group(0) or 'function *' in match.group(0):
                        block.metadata["is_generator"] = True
                    
                    parsed_file.blocks.append(block)
    
    def _parse_classes(self, original: str, content: str, parsed_file: ParsedFile):
        """Parse class declarations"""
        pattern = r'(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+[^{]+)?(?:\s+implements\s+[^{]+)?\s*{'
        
        for match in re.finditer(pattern, content):
            name = match.group(1)
            start_pos = match.start()
            
            # Find class end
            end_pos = self._find_block_end(content, start_pos)
            
            if end_pos > start_pos:
                class_content = original[start_pos:end_pos]
                
                # Extract class signature
                signature = match.group(0).replace('{', '').strip()
                
                # Extract JSDoc
                docstring = self._extract_jsdoc(original, start_pos)
                
                # Calculate line numbers
                start_line = original[:start_pos].count('\n') + 1
                end_line = original[:end_pos].count('\n') + 1
                
                # Create class block
                class_block = CodeBlock(
                    type="class",
                    name=name,
                    content=class_content,
                    docstring=docstring,
                    signature=signature,
                    start_line=start_line,
                    end_line=end_line,
                    language=parsed_file.language.value
                )
                
                # Check modifiers
                if 'export' in match.group(0):
                    parsed_file.exports.append(name)
                    class_block.metadata["exported"] = True
                
                if 'abstract' in match.group(0):
                    class_block.metadata["is_abstract"] = True
                
                # Extract extends and implements
                if 'extends' in match.group(0):
                    extends_match = re.search(r'extends\s+([^{\s]+)', match.group(0))
                    if extends_match:
                        class_block.metadata["extends"] = extends_match.group(1).strip()
                
                if 'implements' in match.group(0):
                    implements_match = re.search(r'implements\s+([^{]+)', match.group(0))
                    if implements_match:
                        class_block.metadata["implements"] = implements_match.group(1).strip()
                
                parsed_file.blocks.append(class_block)
                
                # Parse class methods
                self._parse_class_methods(class_content, name, start_line, parsed_file)
    
    def _parse_class_methods(self, class_content: str, class_name: str, class_start_line: int, parsed_file: ParsedFile):
        """Parse methods within a class"""
        # Pattern for class methods
        patterns = [
            # Regular method
            r'(?:(?:public|private|protected|static|async|readonly)\s+)*(\w+)\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*{',
            # Getter/Setter
            r'(?:get|set)\s+(\w+)\s*\([^)]*\)\s*{',
            # Arrow function property
            r'(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, class_content):
                method_name = match.group(1)
                
                # Skip constructor as it's often handled separately
                if method_name == 'constructor':
                    continue
                
                if method_name and not self._is_keyword(method_name):
                    method_start = match.start()
                    relative_line = class_content[:method_start].count('\n')
                    
                    block = CodeBlock(
                        type="method",
                        name=method_name,
                        content=match.group(0),
                        signature=self._extract_function_signature(match.group(0)),
                        start_line=class_start_line + relative_line,
                        end_line=class_start_line + relative_line + match.group(0).count('\n'),
                        language=parsed_file.language.value,
                        metadata={"class": class_name}
                    )
                    
                    # Check modifiers
                    if 'static' in match.group(0):
                        block.metadata["is_static"] = True
                    if 'private' in match.group(0):
                        block.metadata["visibility"] = "private"
                    elif 'protected' in match.group(0):
                        block.metadata["visibility"] = "protected"
                    else:
                        block.metadata["visibility"] = "public"
                    
                    if 'async' in match.group(0):
                        block.metadata["is_async"] = True
                    
                    if 'get ' in match.group(0):
                        block.type = "getter"
                    elif 'set ' in match.group(0):
                        block.type = "setter"
                    
                    parsed_file.blocks.append(block)
    
    def _parse_interfaces(self, content: str, parsed_file: ParsedFile):
        """Parse TypeScript interfaces"""
        if parsed_file.language != Language.TYPESCRIPT:
            return
        
        pattern = r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+[^{]+)?\s*{'
        
        for match in re.finditer(pattern, content):
            name = match.group(1)
            start_pos = match.start()
            end_pos = self._find_block_end(content, start_pos)
            
            if end_pos > start_pos:
                interface_content = content[start_pos:end_pos]
                start_line = content[:start_pos].count('\n') + 1
                
                block = CodeBlock(
                    type="interface",
                    name=name,
                    content=interface_content,
                    signature=match.group(0).replace('{', '').strip(),
                    start_line=start_line,
                    end_line=content[:end_pos].count('\n') + 1,
                    language="typescript"
                )
                
                if 'export' in match.group(0):
                    parsed_file.exports.append(name)
                    block.metadata["exported"] = True
                
                parsed_file.blocks.append(block)
    
    def _parse_type_aliases(self, content: str, parsed_file: ParsedFile):
        """Parse TypeScript type aliases"""
        if parsed_file.language != Language.TYPESCRIPT:
            return
        
        pattern = r'(?:export\s+)?type\s+(\w+)(?:<[^>]+>)?\s*=\s*([^;]+);'
        
        for match in re.finditer(pattern, content):
            name = match.group(1)
            type_def = match.group(2)
            start_line = content[:match.start()].count('\n') + 1
            
            block = CodeBlock(
                type="type_alias",
                name=name,
                content=match.group(0),
                signature=f"type {name}",
                start_line=start_line,
                end_line=start_line + match.group(0).count('\n'),
                language="typescript",
                metadata={"type_definition": type_def.strip()}
            )
            
            if 'export' in match.group(0):
                parsed_file.exports.append(name)
                block.metadata["exported"] = True
            
            parsed_file.blocks.append(block)
    
    def _parse_enums(self, content: str, parsed_file: ParsedFile):
        """Parse TypeScript enums"""
        if parsed_file.language != Language.TYPESCRIPT:
            return
        
        pattern = r'(?:export\s+)?(?:const\s+)?enum\s+(\w+)\s*{'
        
        for match in re.finditer(pattern, content):
            name = match.group(1)
            start_pos = match.start()
            end_pos = self._find_block_end(content, start_pos)
            
            if end_pos > start_pos:
                enum_content = content[start_pos:end_pos]
                start_line = content[:start_pos].count('\n') + 1
                
                block = CodeBlock(
                    type="enum",
                    name=name,
                    content=enum_content,
                    signature=match.group(0).replace('{', '').strip(),
                    start_line=start_line,
                    end_line=content[:end_pos].count('\n') + 1,
                    language="typescript"
                )
                
                if 'export' in match.group(0):
                    parsed_file.exports.append(name)
                    block.metadata["exported"] = True
                
                if 'const' in match.group(0):
                    block.metadata["is_const"] = True
                
                parsed_file.blocks.append(block)
    
    def _parse_imports(self, content: str, parsed_file: ParsedFile):
        """Parse import statements"""
        patterns = [
            # ES6 imports
            r'import\s+(?:{[^}]+}|\*\s+as\s+\w+|[\w,\s]+)\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'import\s+[\'"]([^\'"]+)[\'"]',
            # CommonJS requires
            r'(?:const|let|var)\s+[\w{},\s]+\s*=\s*require\s*\([\'"]([^\'"]+)[\'"]\)',
            # Dynamic imports
            r'import\s*\([\'"]([^\'"]+)[\'"]\)'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                module = match.group(1)
                if module and module not in parsed_file.imports:
                    parsed_file.imports.append(module)
    
    def _parse_exports(self, content: str, parsed_file: ParsedFile):
        """Parse export statements"""
        patterns = [
            # Named exports
            r'export\s+{([^}]+)}',
            # Default export
            r'export\s+default\s+(\w+)',
            # Direct exports
            r'export\s+(?:const|let|var|function|class)\s+(\w+)',
            # CommonJS exports
            r'module\.exports\s*=\s*(\w+)',
            r'exports\.(\w+)\s*='
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                if pattern == r'export\s+{([^}]+)}':
                    # Handle multiple exports in braces
                    exports = match.group(1).split(',')
                    for exp in exports:
                        exp = exp.strip()
                        if ' as ' in exp:
                            exp = exp.split(' as ')[1].strip()
                        if exp and exp not in parsed_file.exports:
                            parsed_file.exports.append(exp)
                else:
                    export = match.group(1)
                    if export and export not in parsed_file.exports and not self._is_keyword(export):
                        parsed_file.exports.append(export)
    
    def _parse_variables(self, content: str, parsed_file: ParsedFile):
        """Parse global/module-level variables"""
        # Pattern for top-level variable declarations
        pattern = r'^(?:export\s+)?(?:const|let|var)\s+(\w+)(?:\s*:\s*[^=]+)?\s*='
        
        for match in re.finditer(pattern, content, re.MULTILINE):
            var_name = match.group(1)
            if var_name and not self._is_keyword(var_name):
                parsed_file.global_vars.append(var_name)
    
    def _find_block_end(self, content: str, start: int) -> int:
        """Find the end of a code block by matching braces"""
        brace_count = 0
        in_string = False
        string_char = None
        escaped = False
        
        for i in range(start, len(content)):
            char = content[i]
            
            if escaped:
                escaped = False
                continue
            
            if char == '\\':
                escaped = True
                continue
            
            if not in_string:
                if char in '"\'`':
                    in_string = True
                    string_char = char
                elif char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return i + 1
            else:
                if char == string_char:
                    in_string = False
                    string_char = None
        
        return start
    
    def _extract_function_signature(self, declaration: str) -> str:
        """Extract a clean function signature"""
        # Remove body
        signature = declaration.split('{')[0].strip()
        
        # Clean up whitespace
        signature = re.sub(r'\s+', ' ', signature)
        
        return signature
    
    def _extract_jsdoc(self, content: str, position: int) -> Optional[str]:
        """Extract JSDoc comment before a declaration"""
        # Look backwards for JSDoc comment
        before = content[:position]
        
        # Find the last /** ... */ before the position
        jsdoc_pattern = r'/\*\*(.*?)\*/'
        matches = list(re.finditer(jsdoc_pattern, before, re.DOTALL))
        
        if matches:
            last_match = matches[-1]
            # Check if there's no code between JSDoc and declaration
            between = before[last_match.end():].strip()
            if not between or between.startswith('@'):  # Decorators are OK
                jsdoc = last_match.group(1)
                # Clean up JSDoc
                lines = jsdoc.split('\n')
                cleaned = []
                for line in lines:
                    line = line.strip()
                    if line.startswith('*'):
                        line = line[1:].strip()
                    if line:
                        cleaned.append(line)
                return '\n'.join(cleaned) if cleaned else None
        
        return None
    
    def _is_keyword(self, word: str) -> bool:
        """Check if a word is a JavaScript/TypeScript keyword"""
        keywords = {
            'function', 'class', 'const', 'let', 'var', 'if', 'else', 'for',
            'while', 'do', 'switch', 'case', 'break', 'continue', 'return',
            'try', 'catch', 'finally', 'throw', 'new', 'this', 'super',
            'import', 'export', 'default', 'async', 'await', 'yield',
            'typeof', 'instanceof', 'in', 'of', 'delete', 'void',
            'null', 'undefined', 'true', 'false', 'NaN', 'Infinity'
        }
        return word in keywords
    
    def _is_module(self, content: str) -> bool:
        """Check if file uses module syntax"""
        return 'export ' in content or 'import ' in content or 'module.exports' in content
    
    def _is_react_component(self, content: str) -> bool:
        """Check if file contains React components"""
        react_indicators = [
            'import React', 'from "react"', "from 'react'",
            'React.Component', 'React.FC', 'React.useState',
            'jsx', 'tsx', '<div', '<span', '<button'
        ]
        return any(indicator in content for indicator in react_indicators)
    
    def _is_test_file(self, filepath: str, content: str) -> bool:
        """Check if this is a test file"""
        path = Path(filepath)
        
        # Check filename
        test_patterns = ['.test.', '.spec.', '__tests__', 'test_']
        if any(pattern in path.stem.lower() for pattern in test_patterns):
            return True
        
        # Check for test frameworks
        test_indicators = [
            'describe(', 'it(', 'test(', 'expect(',
            'jest', 'mocha', 'chai', 'jasmine', 'vitest',
            'beforeEach', 'afterEach', 'beforeAll', 'afterAll'
        ]
        return any(indicator in content for indicator in test_indicators)
    
    def _detect_framework(self, content: str, imports: List[str]) -> Optional[str]:
        """Detect the framework being used"""
        frameworks = {
            'react': ['react', 'react-dom', 'jsx', 'useState', 'useEffect'],
            'vue': ['vue', 'createApp', '@vue', 'defineComponent'],
            'angular': ['@angular', 'Component', 'Injectable', 'NgModule'],
            'svelte': ['svelte', '.svelte', 'export let'],
            'express': ['express', 'app.get', 'app.post', 'app.listen'],
            'nextjs': ['next', 'next/', 'getServerSideProps', 'getStaticProps'],
            'nuxt': ['nuxt', '@nuxt', 'asyncData', 'fetch'],
            'nodejs': ['http', 'https', 'fs', 'path', 'process.', 'require(']
        }
        
        detected = []
        for framework, indicators in frameworks.items():
            score = sum(1 for indicator in indicators 
                       if indicator in content or any(indicator in imp for imp in imports))
            if score >= 2:
                detected.append(framework)
        
        return ', '.join(detected) if detected else None
