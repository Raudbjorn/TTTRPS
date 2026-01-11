#!/usr/bin/env python3
"""
Claude CLI integration for advanced preprocessing and reranking.
Provides fallback options when Claude is not available.
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import time

logger = logging.getLogger(__name__)


class ClaudeConfig:
    """Configuration for Claude CLI integration"""
    
    def __init__(self,
                 use_claude: bool = True,
                 claude_timeout: int = 30,
                 max_retries: int = 2,
                 fallback_to_ollama: bool = True,
                 ollama_model: str = "llama3.2",
                 cache_responses: bool = True,
                 cache_dir: str = "./claude_cache"):
        
        self.use_claude = use_claude
        self.claude_timeout = claude_timeout
        self.max_retries = max_retries
        self.fallback_to_ollama = fallback_to_ollama
        self.ollama_model = ollama_model
        self.cache_responses = cache_responses
        self.cache_dir = Path(cache_dir)
        
        if cache_responses:
            self.cache_dir.mkdir(parents=True, exist_ok=True)


class ClaudeIntegration:
    """Claude CLI integration for RAG preprocessing and reranking"""
    
    def __init__(self, config: Optional[ClaudeConfig] = None):
        """Initialize Claude integration"""
        self.config = config or ClaudeConfig()
        self.claude_available = self._check_claude_cli()
        self.ollama_available = self._check_ollama() if self.config.fallback_to_ollama else False
        
        if not self.claude_available and self.config.use_claude:
            logger.warning("Claude CLI not available. Will use fallback methods.")
    
    def _check_claude_cli(self) -> bool:
        """Check if Claude CLI is available"""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is available"""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _get_cache_key(self, operation: str, content: str) -> str:
        """Generate cache key for content"""
        import hashlib
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]  # Use SHA256 instead of MD5
        return f"{operation}_{content_hash}"
    
    def _load_from_cache(self, cache_key: str) -> Optional[str]:
        """Load response from cache"""
        if not self.config.cache_responses:
            return None
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    return data.get('response')
            except Exception:
                pass
        return None
    
    def _save_to_cache(self, cache_key: str, response: str):
        """Save response to cache"""
        if not self.config.cache_responses:
            return
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'response': response,
                    'timestamp': time.time()
                }, f)
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")
    
    def _run_claude_cli(self, prompt: str, content: str) -> Optional[str]:
        """Run Claude CLI with prompt and content"""
        if not self.claude_available:
            return None
        
        try:
            # Create temporary file with content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                temp_file = f.name
            
            # Run Claude CLI
            cmd = [
                "claude",
                "-m", "claude-3-haiku-20240307",  # Use fast model
                prompt,
                "-f", temp_file
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.claude_timeout
            )
            
            # Clean up temp file safely
            try:
                Path(temp_file).unlink()
            except (OSError, PermissionError):
                pass  # Will be handled in finally block
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"Claude CLI error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.warning("Claude CLI timed out")
            return None
        except Exception as e:
            logger.error(f"Claude CLI failed: {e}")
            return None
        finally:
            # Ensure temp file is safely cleaned up
            try:
                if 'temp_file' in locals() and temp_file:
                    temp_path = Path(temp_file)
                    if temp_path.exists():
                        temp_path.unlink()
            except (OSError, PermissionError) as e:
                logger.warning(f"Failed to cleanup temporary file {temp_file}: {e}")
    
    def _run_ollama(self, prompt: str, content: str) -> Optional[str]:
        """Run Ollama as fallback"""
        if not self.ollama_available:
            return None
        
        try:
            full_prompt = f"{prompt}\n\nContent:\n{content}"
            
            result = subprocess.run(
                ["ollama", "run", self.config.ollama_model, full_prompt],
                capture_output=True,
                text=True,
                timeout=self.config.claude_timeout
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"Ollama error: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.warning("Ollama timed out")
            return None
        except Exception as e:
            logger.error(f"Ollama failed: {e}")
            return None
    
    def preprocess_json_to_markdown(self, json_content: str) -> str:
        """Convert JSON to markdown using Claude or fallback"""
        
        # Check cache
        cache_key = self._get_cache_key("json_to_md", json_content)
        cached = self._load_from_cache(cache_key)
        if cached:
            return cached
        
        prompt = """Convert this JSON content to clean, readable Markdown format. 
        Focus on creating a well-structured document with:
        - Clear headings and sections
        - Properly formatted lists and tables
        - Code blocks where appropriate
        - Emphasis on readability
        Output only the markdown, no explanations."""
        
        # Try Claude first
        if self.config.use_claude and self.claude_available:
            result = self._run_claude_cli(prompt, json_content)
            if result:
                self._save_to_cache(cache_key, result)
                return result
        
        # Try Ollama fallback
        if self.config.fallback_to_ollama and self.ollama_available:
            result = self._run_ollama(prompt, json_content)
            if result:
                self._save_to_cache(cache_key, result)
                return result
        
        # Basic fallback conversion
        return self._basic_json_to_markdown(json_content)
    
    def _basic_json_to_markdown(self, json_content: str) -> str:
        """Basic JSON to markdown conversion without LLM"""
        try:
            data = json.loads(json_content)
            return self._dict_to_markdown(data)
        except json.JSONDecodeError:
            # If not valid JSON, return as code block
            return f"```json\n{json_content}\n```"
    
    def _dict_to_markdown(self, data: Any, level: int = 1) -> str:
        """Convert dictionary to markdown recursively"""
        lines = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                heading = "#" * min(level, 6)
                lines.append(f"{heading} {key}\n")
                lines.append(self._dict_to_markdown(value, level + 1))
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    lines.append(self._dict_to_markdown(item, level))
                else:
                    lines.append(f"- {item}")
            lines.append("")
        else:
            lines.append(f"{data}\n")
        
        return "\n".join(lines)
    
    def rerank_results(self,
                      query: str,
                      results: List[Dict[str, Any]],
                      top_k: int = 5) -> List[Dict[str, Any]]:
        """Rerank search results using Claude or fallback"""
        
        if not results:
            return []
        
        # Prepare content for reranking
        content = f"Query: {query}\n\n"
        for i, result in enumerate(results[:10]):  # Limit to top 10 for reranking
            content += f"Document {i+1}:\n{result.get('content', '')[:500]}\n\n"
        
        prompt = f"""Rerank these search results for the query. 
        Return only the document numbers in order of relevance (most relevant first).
        Format: comma-separated numbers like "3,1,5,2,4"
        Consider semantic relevance, not just keyword matching."""
        
        # Check cache
        cache_key = self._get_cache_key("rerank", content)
        cached = self._load_from_cache(cache_key)
        
        ranking_str = None
        if cached:
            ranking_str = cached
        elif self.config.use_claude and self.claude_available:
            ranking_str = self._run_claude_cli(prompt, content)
            if ranking_str:
                self._save_to_cache(cache_key, ranking_str)
        elif self.config.fallback_to_ollama and self.ollama_available:
            ranking_str = self._run_ollama(prompt, content)
            if ranking_str:
                self._save_to_cache(cache_key, ranking_str)
        
        if ranking_str:
            try:
                # More robust parsing of ranking results
                # Remove any non-numeric characters and split
                import re
                # Extract numbers from the response, handling various formats
                numbers = re.findall(r'\b(\d+)\b', ranking_str)

                if numbers:
                    rankings = []
                    for num_str in numbers:
                        try:
                            num = int(num_str) - 1  # Convert to 0-based index
                            if 0 <= num < len(results):
                                rankings.append(num)
                        except ValueError:
                            continue

                    # Reorder results based on parsed rankings
                    reranked = []
                    used_indices = set()

                    for idx in rankings[:top_k]:
                        if idx not in used_indices:
                            reranked.append(results[idx])
                            used_indices.add(idx)

                    # Add any missing results up to top_k
                    for i, result in enumerate(results[:top_k]):
                        if i not in used_indices and len(reranked) < top_k:
                            reranked.append(result)

                    return reranked[:top_k]

            except (ValueError, IndexError, AttributeError) as e:
                logger.warning(f"Failed to parse reranking results: {e}")
        
        # Return original order if reranking fails
        return results[:top_k]
    
    def synthesize_answer(self,
                         query: str,
                         context: List[Dict[str, Any]],
                         include_citations: bool = True) -> str:
        """Synthesize answer from context using Claude or fallback"""
        
        # Prepare context
        context_text = ""
        for i, doc in enumerate(context):
            context_text += f"[{i+1}] {doc.get('content', '')}\n\n"
        
        prompt = f"""Answer this query based only on the provided context.
        {'Include inline citations like [1] when referencing sources.' if include_citations else ''}
        Be concise and accurate. If the context doesn't contain the answer, say so.
        
        Query: {query}"""
        
        # Check cache
        cache_key = self._get_cache_key("synthesis", f"{query}_{context_text}")
        cached = self._load_from_cache(cache_key)
        
        if cached:
            return cached
        
        # Try Claude first
        if self.config.use_claude and self.claude_available:
            result = self._run_claude_cli(prompt, context_text)
            if result:
                self._save_to_cache(cache_key, result)
                return result
        
        # Try Ollama fallback
        if self.config.fallback_to_ollama and self.ollama_available:
            result = self._run_ollama(prompt, context_text)
            if result:
                self._save_to_cache(cache_key, result)
                return result
        
        # Basic fallback synthesis
        return self._basic_synthesis(query, context, include_citations)
    
    def _basic_synthesis(self,
                        query: str,
                        context: List[Dict[str, Any]],
                        include_citations: bool = True) -> str:
        """Basic answer synthesis without LLM"""
        if not context:
            return "No relevant information found in the documentation."
        
        # Simple extraction of most relevant content
        answer_parts = []
        for i, doc in enumerate(context[:3]):
            content = doc.get('content', '')[:200]
            if include_citations:
                answer_parts.append(f"{content} [{i+1}]")
            else:
                answer_parts.append(content)
        
        return " ".join(answer_parts)
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text using Claude or fallback"""
        
        prompt = f"""Extract the {max_keywords} most important keywords/phrases from this text.
        Return as comma-separated list. Focus on technical terms and key concepts."""
        
        # Check cache
        cache_key = self._get_cache_key("keywords", text)
        cached = self._load_from_cache(cache_key)
        
        keywords_str = None
        if cached:
            keywords_str = cached
        elif self.config.use_claude and self.claude_available:
            keywords_str = self._run_claude_cli(prompt, text)
            if keywords_str:
                self._save_to_cache(cache_key, keywords_str)
        elif self.config.fallback_to_ollama and self.ollama_available:
            keywords_str = self._run_ollama(prompt, text)
            if keywords_str:
                self._save_to_cache(cache_key, keywords_str)
        
        if keywords_str:
            keywords = [k.strip() for k in keywords_str.split(',')]
            return keywords[:max_keywords]
        
        # Basic keyword extraction
        return self._basic_keyword_extraction(text, max_keywords)
    
    def _basic_keyword_extraction(self, text: str, max_keywords: int = 10) -> List[str]:
        """Basic keyword extraction without LLM"""
        import re
        from collections import Counter
        
        # Simple word frequency approach
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        # Filter common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                    'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'been', 'be'}
        
        words = [w for w in words if w not in stopwords and len(w) > 3]
        
        # Get most common
        word_counts = Counter(words)
        return [word for word, _ in word_counts.most_common(max_keywords)]
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of Claude integration"""
        return {
            "claude_available": self.claude_available,
            "ollama_available": self.ollama_available,
            "cache_enabled": self.config.cache_responses,
            "cache_dir": str(self.config.cache_dir),
            "fallback_enabled": self.config.fallback_to_ollama,
            "ollama_model": self.config.ollama_model if self.ollama_available else None
        }


def create_claude_integration(use_claude: bool = True,
                             fallback_to_ollama: bool = True,
                             cache_responses: bool = True) -> ClaudeIntegration:
    """Factory function to create Claude integration"""
    
    config = ClaudeConfig(
        use_claude=use_claude,
        fallback_to_ollama=fallback_to_ollama,
        cache_responses=cache_responses
    )
    
    return ClaudeIntegration(config)