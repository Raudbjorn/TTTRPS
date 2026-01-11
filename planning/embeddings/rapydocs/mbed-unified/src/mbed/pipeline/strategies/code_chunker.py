"""
Code-aware chunking strategy using AST-based analysis
"""

import re
import ast
import logging
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass
from ..chunker import ChunkingStrategy, Chunk, ChunkConfig
from ...core.result import Result

logger = logging.getLogger(__name__)


@dataclass
class CodeStructure:
    """Represents a code structure element (function, class, etc.)."""
    name: str
    type: str  # 'function', 'class', 'method', 'import', 'comment', 'docstring'
    start_line: int
    end_line: int
    content: str
    metadata: Dict[str, Any]


class CodeChunker(ChunkingStrategy):
    """Code-aware chunking using AST analysis and syntax understanding."""

    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        self.tokenizer = None
        self.tree_sitter_available = False
        self._setup_dependencies()

    def _setup_dependencies(self):
        """Setup tokenizer and tree-sitter with fallbacks."""
        try:
            import tiktoken
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            logger.debug("Using tiktoken for token counting")
        except ImportError:
            logger.debug("tiktoken not available, falling back to word-based counting")
            self.tokenizer = None

        try:
            import tree_sitter
            self.tree_sitter_available = True
            logger.debug("Tree-sitter available for advanced AST parsing")
        except ImportError:
            logger.debug("Tree-sitter not available, using Python AST only")
            self.tree_sitter_available = False

    def chunk(self, text: str, config: ChunkConfig) -> Result[List[Chunk], str]:
        """Chunk text using code-aware strategy with AST analysis."""
        # Validate inputs
        if not text or not text.strip():
            return Result.Ok([])

        validation = self.validate_config(config)
        if validation.is_err():
            return validation

        try:
            # Preprocess text
            processed_text = self.preprocess(text)

            # Detect programming language
            language = self._detect_language(processed_text, config)

            # Extract code structures based on language
            if language == 'python':
                structures = self._analyze_python_code(processed_text)
            elif language in ['javascript', 'typescript']:
                structures = self._analyze_javascript_code(processed_text)
            elif language in ['java', 'c', 'cpp']:
                structures = self._analyze_c_like_code(processed_text, language)
            else:
                # Fallback to generic code analysis
                structures = self._analyze_generic_code(processed_text)

            # Create chunks based on code structures
            chunks = self._create_code_chunks(processed_text, structures, config, language)

            return Result.Ok(chunks)

        except Exception as e:
            return Result.Err(f"Code chunking failed: {str(e)}")

    def _detect_language(self, text: str) -> str:
        """Detect programming language from code content."""
        # Check for language indicators
        indicators = {
            'python': [
                r'def\s+\w+\s*\(',
                r'class\s+\w+\s*[:(]',
                r'import\s+\w+',
                r'from\s+\w+\s+import',
                r'if\s+__name__\s*==\s*["\']__main__["\']',
                r'@\w+',  # decorators
            ],
            'javascript': [
                r'function\s+\w+\s*\(',
                r'const\s+\w+\s*=',
                r'let\s+\w+\s*=',
                r'var\s+\w+\s*=',
                r'console\.log\s*\(',
                r'require\s*\(',
                r'module\.exports',
            ],
            'typescript': [
                r'interface\s+\w+',
                r'type\s+\w+\s*=',
                r'enum\s+\w+',
                r':\s*\w+\s*[=;]',  # type annotations
                r'export\s+(?:interface|type|enum)',
            ],
            'java': [
                r'public\s+class\s+\w+',
                r'private\s+\w+\s+\w+',
                r'public\s+static\s+void\s+main',
                r'import\s+[\w.]+;',
                r'@Override',
            ],
            'c': [
                r'#include\s*<[\w.]+>',
                r'int\s+main\s*\(',
                r'printf\s*\(',
                r'void\s+\w+\s*\(',
                r'struct\s+\w+',
            ],
            'cpp': [
                r'#include\s*<[\w.]+>',
                r'using\s+namespace',
                r'std::',
                r'class\s+\w+',
                r'public:',
                r'private:',
            ]
        }

        # Count matches for each language
        language_scores = {}
        for lang, patterns in indicators.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE | re.MULTILINE))
                score += matches
            language_scores[lang] = score

        # Return language with highest score, or 'generic' if no clear winner
        if language_scores:
            best_lang = max(language_scores.items(), key=lambda x: x[1])
            if best_lang[1] > 0:
                return best_lang[0]

        return 'generic'

    def _analyze_python_code(self, code: str) -> List[CodeStructure]:
        """Analyze Python code using AST."""
        structures = []

        try:
            # Parse with Python AST
            tree = ast.parse(code)

            lines = code.splitlines()

            for node in ast.walk(tree):
                structure = None

                if isinstance(node, ast.FunctionDef):
                    structure = self._create_python_function_structure(node, lines)
                elif isinstance(node, ast.ClassDef):
                    structure = self._create_python_class_structure(node, lines)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    structure = self._create_python_import_structure(node, lines)

                if structure:
                    structures.append(structure)

            # Sort by line number
            structures.sort(key=lambda s: s.start_line)

        except SyntaxError as e:
            logger.warning(f"Python AST parsing failed: {e}, falling back to regex")
            structures = self._analyze_python_regex(code)
        except Exception as e:
            logger.warning(f"Python analysis failed: {e}")
            structures = []

        return structures

    def _create_python_function_structure(self, node: ast.FunctionDef, lines: List[str]) -> CodeStructure:
        """Create structure for Python function."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line

        # Extract function content
        content_lines = lines[start_line - 1:end_line]
        content = '\n'.join(content_lines)

        # Extract metadata
        metadata = {
            'args': [arg.arg for arg in node.args.args],
            'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
            'is_async': isinstance(node, ast.AsyncFunctionDef),
            'docstring': ast.get_docstring(node)
        }

        return CodeStructure(
            name=node.name,
            type='function',
            start_line=start_line,
            end_line=end_line,
            content=content,
            metadata=metadata
        )

    def _create_python_class_structure(self, node: ast.ClassDef, lines: List[str]) -> CodeStructure:
        """Create structure for Python class."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line

        content_lines = lines[start_line - 1:end_line]
        content = '\n'.join(content_lines)

        # Extract methods
        methods = []
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                methods.append(child.name)

        metadata = {
            'bases': [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases],
            'methods': methods,
            'decorators': [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list],
            'docstring': ast.get_docstring(node)
        }

        return CodeStructure(
            name=node.name,
            type='class',
            start_line=start_line,
            end_line=end_line,
            content=content,
            metadata=metadata
        )

    def _create_python_import_structure(self, node: Union[ast.Import, ast.ImportFrom], lines: List[str]) -> CodeStructure:
        """Create structure for Python import."""
        start_line = node.lineno
        end_line = node.end_lineno or start_line

        content_lines = lines[start_line - 1:end_line]
        content = '\n'.join(content_lines)

        if isinstance(node, ast.ImportFrom):
            name = f"from {node.module}"
            metadata = {'module': node.module, 'names': [alias.name for alias in node.names]}
        else:
            name = "import"
            metadata = {'names': [alias.name for alias in node.names]}

        return CodeStructure(
            name=name,
            type='import',
            start_line=start_line,
            end_line=end_line,
            content=content,
            metadata=metadata
        )

    def _analyze_python_regex(self, code: str) -> List[CodeStructure]:
        """Fallback Python analysis using regex."""
        structures = []
        lines = code.splitlines()

        # Find functions
        for match in re.finditer(r'^(\s*)def\s+(\w+)\s*\((.*?)\):', code, re.MULTILINE):
            start_line = code[:match.start()].count('\n') + 1
            indent = len(match.group(1))

            # Find function end by tracking indentation
            end_line = self._find_block_end(lines, start_line - 1, indent)

            content_lines = lines[start_line - 1:end_line]
            content = '\n'.join(content_lines)

            structures.append(CodeStructure(
                name=match.group(2),
                type='function',
                start_line=start_line,
                end_line=end_line,
                content=content,
                metadata={'args_string': match.group(3)}
            ))

        # Find classes
        for match in re.finditer(r'^(\s*)class\s+(\w+)(?:\([^)]*\))?:', code, re.MULTILINE):
            start_line = code[:match.start()].count('\n') + 1
            indent = len(match.group(1))

            end_line = self._find_block_end(lines, start_line - 1, indent)

            content_lines = lines[start_line - 1:end_line]
            content = '\n'.join(content_lines)

            structures.append(CodeStructure(
                name=match.group(2),
                type='class',
                start_line=start_line,
                end_line=end_line,
                content=content,
                metadata={}
            ))

        return sorted(structures, key=lambda s: s.start_line)

    def _analyze_javascript_code(self, code: str) -> List[CodeStructure]:
        """Analyze JavaScript/TypeScript code using regex patterns."""
        structures = []
        lines = code.splitlines()

        # Function declarations
        patterns = [
            (r'function\s+(\w+)\s*\([^)]*\)\s*{', 'function'),
            (r'const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>\s*{?', 'arrow_function'),
            (r'class\s+(\w+)(?:\s+extends\s+\w+)?\s*{', 'class'),
            (r'interface\s+(\w+)\s*{', 'interface'),
            (r'type\s+(\w+)\s*=', 'type_alias'),
        ]

        for pattern, struct_type in patterns:
            for match in re.finditer(pattern, code, re.MULTILINE):
                start_line = code[:match.start()].count('\n') + 1
                name = match.group(1)

                # Find end by brace matching or other heuristics
                end_line = self._find_js_block_end(lines, start_line - 1)

                content_lines = lines[start_line - 1:end_line]
                content = '\n'.join(content_lines)

                structures.append(CodeStructure(
                    name=name,
                    type=struct_type,
                    start_line=start_line,
                    end_line=end_line,
                    content=content,
                    metadata={}
                ))

        return sorted(structures, key=lambda s: s.start_line)

    def _analyze_c_like_code(self, code: str, language: str) -> List[CodeStructure]:
        """Analyze C/C++/Java code using regex patterns."""
        structures = []
        lines = code.splitlines()

        # Common patterns for C-like languages
        patterns = []

        if language == 'java':
            patterns = [
                (r'public\s+class\s+(\w+)', 'class'),
                (r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*{', 'method'),
                (r'interface\s+(\w+)', 'interface'),
            ]
        elif language in ['c', 'cpp']:
            patterns = [
                (r'(?:struct|class)\s+(\w+)', 'struct_class'),
                (r'(?:\w+\s+)*(\w+)\s*\([^)]*\)\s*{', 'function'),
                (r'#include\s*[<"]([^>"]+)[>"]', 'include'),
            ]

        for pattern, struct_type in patterns:
            for match in re.finditer(pattern, code, re.MULTILINE):
                start_line = code[:match.start()].count('\n') + 1
                name = match.group(1)

                # Estimate end line
                end_line = self._find_c_block_end(lines, start_line - 1)

                content_lines = lines[start_line - 1:end_line]
                content = '\n'.join(content_lines)

                structures.append(CodeStructure(
                    name=name,
                    type=struct_type,
                    start_line=start_line,
                    end_line=end_line,
                    content=content,
                    metadata={}
                ))

        return sorted(structures, key=lambda s: s.start_line)

    def _analyze_generic_code(self, code: str) -> List[CodeStructure]:
        """Generic code analysis for unknown languages."""
        structures = []
        lines = code.splitlines()

        # Look for comment blocks
        in_comment_block = False
        comment_start = 0

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Detect comment blocks
            if not in_comment_block and (stripped.startswith('/*') or stripped.startswith('/**')):
                in_comment_block = True
                comment_start = i
            elif in_comment_block and ('*/' in stripped):
                in_comment_block = False
                content = '\n'.join(lines[comment_start:i + 1])
                structures.append(CodeStructure(
                    name=f"comment_block_{comment_start + 1}",
                    type='comment',
                    start_line=comment_start + 1,
                    end_line=i + 1,
                    content=content,
                    metadata={}
                ))

            # Detect function-like patterns
            if re.match(r'^\s*\w+\s+\w+\s*\([^)]*\)', line):
                structures.append(CodeStructure(
                    name=f"function_{i + 1}",
                    type='function',
                    start_line=i + 1,
                    end_line=i + 1,
                    content=line,
                    metadata={}
                ))

        return structures

    def _find_block_end(self, lines: List[str], start_line: int, base_indent: int) -> int:
        """Find the end of a Python code block by tracking indentation."""
        for i in range(start_line + 1, len(lines)):
            line = lines[i]
            if line.strip():  # Non-empty line
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= base_indent:
                    return i
        return len(lines)

    def _find_js_block_end(self, lines: List[str], start_line: int) -> int:
        """Find the end of a JavaScript block by tracking braces."""
        brace_count = 0
        found_opening = False

        for i in range(start_line, len(lines)):
            line = lines[i]
            for char in line:
                if char == '{':
                    brace_count += 1
                    found_opening = True
                elif char == '}':
                    brace_count -= 1
                    if found_opening and brace_count == 0:
                        return i + 1

        return min(start_line + 50, len(lines))  # Reasonable fallback

    def _find_c_block_end(self, lines: List[str], start_line: int) -> int:
        """Find the end of a C-like block."""
        # Similar to JavaScript but with different heuristics
        return self._find_js_block_end(lines, start_line)

    def _create_code_chunks(
        self, code: str, structures: List[CodeStructure], config: ChunkConfig, language: str
    ) -> List[Chunk]:
        """Create chunks based on code structures."""
        if not structures:
            # Fallback to simple line-based chunking
            return self._create_line_based_chunks(code, config, language)

        chunks = []
        lines = code.splitlines()

        # Group structures into chunks
        current_structures = []
        current_lines = []
        current_tokens = 0
        chunk_index = 0

        for structure in structures:
            structure_tokens = self._count_tokens(structure.content)

            # Check if we should start a new chunk
            if current_tokens + structure_tokens > config.size and current_structures:
                # Create chunk from current structures
                chunk = self._create_structure_chunk(
                    current_structures, current_lines, chunk_index, language
                )
                chunks.append(chunk)

                current_structures = [structure]
                current_lines = lines[structure.start_line - 1:structure.end_line]
                current_tokens = structure_tokens
                chunk_index += 1
            else:
                current_structures.append(structure)
                if not current_lines:
                    current_lines = lines[structure.start_line - 1:structure.end_line]
                else:
                    # Extend lines to include new structure
                    end_line = max(len(current_lines), structure.end_line)
                    current_lines = lines[min(s.start_line for s in current_structures) - 1:end_line]
                current_tokens += structure_tokens

            # Safety check
            if chunk_index > 10000:
                logger.warning("Maximum chunk limit reached in code chunking")
                break

        # Handle remaining structures
        if current_structures:
            chunk = self._create_structure_chunk(
                current_structures, current_lines, chunk_index, language
            )
            chunks.append(chunk)

        return chunks

    def _create_structure_chunk(
        self, structures: List[CodeStructure], lines: List[str], chunk_index: int, language: str
    ) -> Chunk:
        """Create a chunk from code structures."""
        chunk_text = '\n'.join(lines)

        # Analyze structures in chunk
        structure_types = [s.type for s in structures]
        structure_names = [s.name for s in structures]

        # Calculate complexity metrics
        complexity_score = self._calculate_complexity(chunk_text, language)

        metadata = {
            'strategy': 'code',
            'language': language,
            'token_count': self._count_tokens(chunk_text),
            'line_count': len(lines),
            'structure_count': len(structures),
            'structure_types': structure_types,
            'structure_names': structure_names,
            'complexity_score': complexity_score,
            'chunk_index': chunk_index,
            'has_functions': 'function' in structure_types,
            'has_classes': 'class' in structure_types,
            'has_comments': 'comment' in structure_types
        }

        # Add language-specific metadata
        if language == 'python':
            metadata.update({
                'has_decorators': any('@' in s.content for s in structures),
                'has_docstrings': any(s.metadata.get('docstring') for s in structures),
                'async_functions': sum(1 for s in structures if s.metadata.get('is_async'))
            })

        return Chunk(
            text=chunk_text,
            metadata=metadata,
            start_idx=0,
            end_idx=len(chunk_text),
            chunk_id=self.generate_chunk_id(chunk_text, chunk_index)
        )

    def _create_line_based_chunks(self, code: str, config: ChunkConfig, language: str) -> List[Chunk]:
        """Fallback to line-based chunking for code without clear structures."""
        lines = code.splitlines()
        chunks = []
        current_lines = []
        current_tokens = 0
        chunk_index = 0

        target_lines = min(config.size // 10, 100)  # Rough estimate: 10 tokens per line

        for line in lines:
            line_tokens = self._count_tokens(line)

            if len(current_lines) >= target_lines or current_tokens + line_tokens > config.size:
                if current_lines:
                    chunk_text = '\n'.join(current_lines)
                    chunk = Chunk(
                        text=chunk_text,
                        metadata={
                            'strategy': 'code_lines',
                            'language': language,
                            'token_count': current_tokens,
                            'line_count': len(current_lines),
                            'chunk_index': chunk_index
                        },
                        start_idx=0,
                        end_idx=len(chunk_text),
                        chunk_id=self.generate_chunk_id(chunk_text, chunk_index)
                    )
                    chunks.append(chunk)

                current_lines = [line]
                current_tokens = line_tokens
                chunk_index += 1
            else:
                current_lines.append(line)
                current_tokens += line_tokens

        # Handle remaining lines
        if current_lines:
            chunk_text = '\n'.join(current_lines)
            chunk = Chunk(
                text=chunk_text,
                metadata={
                    'strategy': 'code_lines',
                    'language': language,
                    'token_count': current_tokens,
                    'line_count': len(current_lines),
                    'chunk_index': chunk_index
                },
                start_idx=0,
                end_idx=len(chunk_text),
                chunk_id=self.generate_chunk_id(chunk_text, chunk_index)
            )
            chunks.append(chunk)

        return chunks

    def _calculate_complexity(self, code: str, language: str) -> float:
        """Calculate a simple complexity score for code."""
        complexity = 0

        # Count control flow statements
        control_patterns = [
            r'\bif\b', r'\belse\b', r'\belif\b', r'\bwhile\b', r'\bfor\b',
            r'\btry\b', r'\bexcept\b', r'\bfinally\b', r'\bswitch\b', r'\bcase\b'
        ]

        for pattern in control_patterns:
            complexity += len(re.findall(pattern, code, re.IGNORECASE))

        # Normalize by lines of code
        lines = len([line for line in code.splitlines() if line.strip()])
        return complexity / max(lines, 1)

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken or word-based fallback."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # For code, count words but give more weight to symbols
            words = len(text.split())
            symbols = len(re.findall(r'[{}()\[\];,.]', text))
            return words + symbols // 2

    def validate_config(self, config: ChunkConfig) -> Result[None, str]:
        """Validate configuration for code-aware chunking."""
        if config.size <= 0:
            return Result.Err("Chunk size must be positive")

        if config.overlap < 0:
            return Result.Err("Overlap cannot be negative")

        # Code-specific warnings
        if config.size < 200:
            logger.warning("Small chunk size may break code structure integrity")

        if config.size > 5000:
            logger.warning("Very large chunks may mix unrelated code functions")

        return Result.Ok(None)


# Registration handled in chunker.py to avoid circular imports