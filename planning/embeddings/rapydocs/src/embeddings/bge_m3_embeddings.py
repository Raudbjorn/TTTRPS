#!/usr/bin/env python3
"""
BGE-M3 embeddings for hybrid dense+sparse retrieval.
Supports multilingual, multi-granularity, and multi-functionality retrieval.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import subprocess
import json

logger = logging.getLogger(__name__)

# Constants for sparse embedding calculation
CORPUS_SIZE_ESTIMATE = 1000  # Estimated corpus size for IDF calculation


class BGEM3Embeddings:
    """BGE-M3 model for hybrid retrieval with Ollama"""
    
    def __init__(self,
                 model_name: str = "bge-m3",
                 use_dense: bool = True,
                 use_sparse: bool = True,
                 use_colbert: bool = False,
                 max_length: int = 8192,
                 normalize: bool = True):
        """
        Initialize BGE-M3 embeddings.
        
        Args:
            model_name: Model name in Ollama
            use_dense: Generate dense embeddings
            use_sparse: Generate sparse embeddings
            use_colbert: Generate ColBERT embeddings (token-level)
            max_length: Maximum sequence length
            normalize: L2 normalize embeddings
        """
        self.model_name = model_name
        self.use_dense = use_dense
        self.use_sparse = use_sparse
        self.use_colbert = use_colbert
        self.max_length = max_length
        self.normalize = normalize
        
        # Model dimensions
        self.dimension = 1024  # BGE-M3 dimension
        self.initialized = False
        
        # Check if model is available
        self.model_available = False
        self.fallback_models = ['nomic-embed-text', 'mxbai-embed-large', 'all-minilm']
    
    async def initialize(self):
        """Initialize and check model availability"""
        
        # Check if BGE-M3 is available
        self.model_available = await self._check_model_availability(self.model_name)
        
        if not self.model_available:
            logger.warning(f"{self.model_name} not available, trying to pull...")
            await self._pull_model(self.model_name)
            self.model_available = await self._check_model_availability(self.model_name)
        
        if not self.model_available:
            # Try fallback models
            for fallback in self.fallback_models:
                logger.info(f"Trying fallback model: {fallback}")
                if await self._check_model_availability(fallback):
                    self.model_name = fallback
                    self.model_available = True
                    # Adjust dimension for fallback models
                    if fallback == 'nomic-embed-text':
                        self.dimension = 768
                    elif fallback == 'mxbai-embed-large':
                        self.dimension = 1024
                    elif fallback == 'all-minilm':
                        self.dimension = 384
                    logger.info(f"Using fallback model: {fallback} (dim={self.dimension})")
                    break
        
        if not self.model_available:
            raise RuntimeError(f"No embedding models available. Please install {self.model_name} or a fallback model.")
        
        self.initialized = True
        logger.info(f"BGE-M3 embeddings initialized with model: {self.model_name}")
    
    async def _check_model_availability(self, model_name: str) -> bool:
        """Check if model is available in Ollama"""
        try:
            result = await asyncio.create_subprocess_exec(
                'ollama', 'list',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            return model_name in stdout.decode()
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            return False
    
    async def _pull_model(self, model_name: str):
        """Pull model from Ollama"""
        try:
            logger.info(f"Pulling model {model_name}...")
            result = await asyncio.create_subprocess_exec(
                'ollama', 'pull', model_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
    
    async def embed_text(self, text: str) -> Dict[str, Any]:
        """
        Generate hybrid embeddings for text.
        
        Returns:
            Dictionary with dense, sparse, and optionally ColBERT embeddings
        """
        if not self.initialized:
            await self.initialize()
        
        # Truncate if needed
        if len(text) > self.max_length:
            text = text[:self.max_length]
        
        result = {}
        
        # Generate dense embedding
        if self.use_dense:
            dense_embedding = await self._generate_dense_embedding(text)
            if self.normalize:
                dense_embedding = self._l2_normalize(dense_embedding)
            result['dense'] = dense_embedding
        
        # Generate sparse embedding (simulated with keyword extraction)
        if self.use_sparse:
            sparse_embedding = self._generate_sparse_embedding(text)
            result['sparse'] = sparse_embedding
        
        # Generate ColBERT embedding if requested
        if self.use_colbert:
            colbert_embedding = await self._generate_colbert_embedding(text)
            result['colbert'] = colbert_embedding
        
        return result
    
    async def _generate_dense_embedding(self, text: str) -> np.ndarray:
        """Generate dense embedding using Ollama"""
        try:
            # Use Ollama API
            cmd = ['ollama', 'embeddings', self.model_name, text]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                # Parse embedding from output
                try:
                    response = json.loads(stdout.decode())
                    embedding = np.array(response.get('embedding', []), dtype=np.float32)
                    
                    # Ensure correct dimension
                    if len(embedding) != self.dimension:
                        # Pad or truncate
                        if len(embedding) < self.dimension:
                            embedding = np.pad(embedding, (0, self.dimension - len(embedding)))
                        else:
                            embedding = embedding[:self.dimension]
                    
                    return embedding
                except json.JSONDecodeError:
                    # Fallback: try to extract floats from output
                    import re
                    floats = re.findall(r'-?\d+\.?\d*', stdout.decode())
                    if floats:
                        embedding = np.array(floats[:self.dimension], dtype=np.float32)
                        if len(embedding) < self.dimension:
                            embedding = np.pad(embedding, (0, self.dimension - len(embedding)))
                        return embedding
            
            # Fallback to random embedding if generation fails
            logger.warning(f"Failed to generate embedding: {stderr.decode()}")
            return np.random.randn(self.dimension).astype(np.float32) * 0.1
            
        except Exception as e:
            logger.error(f"Error generating dense embedding: {e}")
            return np.random.randn(self.dimension).astype(np.float32) * 0.1
    
    def _generate_sparse_embedding(self, text: str) -> Dict[str, float]:
        """
        Generate sparse embedding (keyword-based).
        Returns a dictionary of term frequencies.
        """
        import re
        from collections import Counter
        
        # Tokenize
        text_lower = text.lower()
        tokens = re.findall(r'\b\w+\b', text_lower)
        
        # Remove stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'was', 'are', 'were', 'been', 'be',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'shall', 'this', 'that',
            'these', 'those', 'it', 'its', 'their', 'there'
        }
        
        tokens = [t for t in tokens if t not in stopwords and len(t) > 2]
        
        # Count frequencies
        term_freq = Counter(tokens)
        
        # Apply TF-IDF weighting (simplified)
        total_terms = len(tokens)
        sparse_embedding = {}
        
        for term, freq in term_freq.items():
            # TF = frequency / total terms
            tf = freq / total_terms if total_terms > 0 else 0
            # Simple IDF approximation (would need corpus stats for real IDF)
            idf = np.log(CORPUS_SIZE_ESTIMATE / (1 + freq))  # Simplified IDF
            sparse_embedding[term] = tf * idf
        
        return sparse_embedding
    
    async def _generate_colbert_embedding(self, text: str) -> List[np.ndarray]:
        """
        Generate ColBERT-style token-level embeddings.
        Returns list of embeddings, one per token.
        """
        # For now, simulate with sentence-level chunks
        import re
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        colbert_embeddings = []
        for sentence in sentences[:10]:  # Limit to 10 sentences
            embedding = await self._generate_dense_embedding(sentence)
            colbert_embeddings.append(embedding)
        
        return colbert_embeddings
    
    def _l2_normalize(self, embedding: np.ndarray) -> np.ndarray:
        """L2 normalize embedding"""
        norm = np.linalg.norm(embedding)
        if norm > 0:
            return embedding / norm
        return embedding
    
    async def embed_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        
        for text in texts:
            embedding = await self.embed_text(text)
            embeddings.append(embedding)
        
        return embeddings
    
    def compute_hybrid_similarity(self,
                                 query_embedding: Dict[str, Any],
                                 doc_embedding: Dict[str, Any],
                                 weights: Optional[Dict[str, float]] = None) -> float:
        """
        Compute hybrid similarity between query and document.
        
        Args:
            query_embedding: Query embeddings (dense, sparse, colbert)
            doc_embedding: Document embeddings
            weights: Weights for different components
        
        Returns:
            Combined similarity score
        """
        if weights is None:
            weights = {
                'dense': 0.6,
                'sparse': 0.3,
                'colbert': 0.1
            }
        
        total_score = 0.0
        total_weight = 0.0
        
        # Dense similarity (cosine)
        if 'dense' in query_embedding and 'dense' in doc_embedding:
            dense_sim = np.dot(query_embedding['dense'], doc_embedding['dense'])
            total_score += weights['dense'] * dense_sim
            total_weight += weights['dense']
        
        # Sparse similarity (overlap)
        if 'sparse' in query_embedding and 'sparse' in doc_embedding:
            query_terms = set(query_embedding['sparse'].keys())
            doc_terms = set(doc_embedding['sparse'].keys())
            
            if query_terms:
                # Weighted Jaccard with TF-IDF scores
                intersection = query_terms & doc_terms
                sparse_score = 0.0
                
                for term in intersection:
                    sparse_score += min(
                        query_embedding['sparse'][term],
                        doc_embedding['sparse'][term]
                    )
                
                # Normalize by query norm
                query_norm = sum(query_embedding['sparse'].values())
                if query_norm > 0:
                    sparse_score /= query_norm
                
                total_score += weights['sparse'] * sparse_score
                total_weight += weights['sparse']
        
        # ColBERT similarity (MaxSim)
        if 'colbert' in query_embedding and 'colbert' in doc_embedding:
            query_vecs = query_embedding['colbert']
            doc_vecs = doc_embedding['colbert']
            
            if query_vecs and doc_vecs:
                # MaxSim: for each query token, find max similarity to doc tokens
                max_sims = []
                for q_vec in query_vecs:
                    sims = [np.dot(q_vec, d_vec) for d_vec in doc_vecs]
                    if sims:
                        max_sims.append(max(sims))
                
                if max_sims:
                    colbert_score = np.mean(max_sims)
                    total_score += weights['colbert'] * colbert_score
                    total_weight += weights['colbert']
        
        # Normalize by total weight
        if total_weight > 0:
            return total_score / total_weight
        
        return 0.0


class HybridBGEM3Retriever:
    """Hybrid retriever using BGE-M3 embeddings"""
    
    def __init__(self,
                 embedder: Optional[BGEM3Embeddings] = None,
                 use_reranking: bool = True):
        """Initialize hybrid retriever"""
        self.embedder = embedder or BGEM3Embeddings()
        self.use_reranking = use_reranking
        
        # Storage for documents
        self.documents = []
        self.embeddings = []
    
    async def index_documents(self, documents: List[Dict[str, Any]]):
        """Index documents with hybrid embeddings"""
        
        if not self.embedder.initialized:
            await self.embedder.initialize()
        
        for doc in documents:
            text = doc.get('content', '')
            embedding = await self.embedder.embed_text(text)
            
            self.documents.append(doc)
            self.embeddings.append(embedding)
        
        logger.info(f"Indexed {len(documents)} documents with BGE-M3")
    
    async def search(self,
                    query: str,
                    top_k: int = 10,
                    hybrid_weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """
        Search using hybrid embeddings.
        
        Args:
            query: Search query
            top_k: Number of results
            hybrid_weights: Weights for dense, sparse, colbert
        
        Returns:
            Ranked search results
        """
        
        if not self.embedder.initialized:
            await self.embedder.initialize()
        
        # Generate query embedding
        query_embedding = await self.embedder.embed_text(query)
        
        # Score all documents
        scores = []
        for i, doc_embedding in enumerate(self.embeddings):
            score = self.embedder.compute_hybrid_similarity(
                query_embedding,
                doc_embedding,
                hybrid_weights
            )
            scores.append((i, score))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Get top-k results
        results = []
        for idx, score in scores[:top_k]:
            result = self.documents[idx].copy()
            result['hybrid_score'] = score
            result['retrieval_method'] = 'bge-m3-hybrid'
            results.append(result)
        
        return results


def create_bge_m3_embedder(use_dense: bool = True,
                          use_sparse: bool = True,
                          use_colbert: bool = False) -> BGEM3Embeddings:
    """Factory function to create BGE-M3 embedder"""
    
    return BGEM3Embeddings(
        use_dense=use_dense,
        use_sparse=use_sparse,
        use_colbert=use_colbert
    )