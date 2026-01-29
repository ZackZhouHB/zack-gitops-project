"""
Embedding generation using Bedrock Titan or local Ollama.

EMBEDDING MODELS:
- Bedrock Titan v2: 1024 dimensions, good quality, ~$0.0001/1K tokens
- Ollama nomic-embed-text: 768 dimensions, free, runs locally
- OpenAI ada-002: 1536 dimensions, good quality, ~$0.0001/1K tokens

WHY TITAN V2?
- AWS native (no external API keys)
- Good quality for enterprise docs
- 1024 dimensions (good balance of quality vs storage)
"""

import json
from abc import ABC, abstractmethod
from typing import Sequence
import boto3


class BaseEmbedder(ABC):
    """Base class for embedding generators."""
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return embedding dimensions."""
        pass
    
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a single text."""
        pass
    
    def embed_batch(self, texts: Sequence[str], batch_size: int = 20) -> list[list[float]]:
        """Embed multiple texts. Override for batch-optimized implementations."""
        return [self.embed(text) for text in texts]


class BedrockEmbedder(BaseEmbedder):
    """
    Generate embeddings using Bedrock Titan Text Embeddings V2.
    
    COST: ~$0.0001 per 1,000 tokens (~$0.10 per 1M tokens)
    
    For 10,000 chunks averaging 500 tokens each:
    - Total tokens: 5,000,000
    - Cost: ~$0.50 (one-time for indexing)
    """
    
    MODEL_ID = "amazon.titan-embed-text-v2:0"
    DIMENSIONS = 1024
    
    def __init__(self, profile: str = "default", region: str = "ap-southeast-2"):
        session = boto3.Session(profile_name=profile, region_name=region)
        self.client = session.client("bedrock-runtime")
    
    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS
    
    def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        body = json.dumps({
            "inputText": text,
            "dimensions": self.DIMENSIONS,
            "normalize": True  # L2 normalize for cosine similarity
        })
        
        response = self.client.invoke_model(
            modelId=self.MODEL_ID,
            body=body
        )
        
        result = json.loads(response["body"].read())
        return result["embedding"]
    
    def embed_batch(self, texts: Sequence[str], batch_size: int = 20) -> list[list[float]]:
        """
        Embed multiple texts.
        
        NOTE: Titan doesn't have native batch API, so we call sequentially.
        For production, consider using async or threading.
        """
        embeddings = []
        for i, text in enumerate(texts):
            if i > 0 and i % 100 == 0:
                print(f"  Embedded {i}/{len(texts)} chunks...")
            embeddings.append(self.embed(text))
        return embeddings


class OllamaEmbedder(BaseEmbedder):
    """
    Generate embeddings using local Ollama.
    
    MODELS:
    - nomic-embed-text: 768 dimensions, good quality
    - mxbai-embed-large: 1024 dimensions, better quality
    
    COST: Free (runs locally)
    
    SETUP:
    1. Install Ollama: brew install ollama
    2. Pull model: ollama pull nomic-embed-text
    3. Start server: ollama serve
    """
    
    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self._dimensions = None
    
    @property
    def dimensions(self) -> int:
        if self._dimensions is None:
            # Get dimensions by embedding a test string
            test_embedding = self.embed("test")
            self._dimensions = len(test_embedding)
        return self._dimensions
    
    def embed(self, text: str) -> list[float]:
        """Generate embedding using Ollama API."""
        import requests
        
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": self.model,
                "prompt": text
            }
        )
        response.raise_for_status()
        return response.json()["embedding"]


class HybridEmbedder:
    """
    Use Bedrock when available, fall back to Ollama.
    
    USEFUL FOR:
    - Development: Use Ollama locally (free)
    - Production: Use Bedrock (better quality)
    - Offline: Fall back to Ollama
    """
    
    def __init__(self, prefer_bedrock: bool = True):
        self.prefer_bedrock = prefer_bedrock
        self._embedder = None
    
    @property
    def embedder(self) -> BaseEmbedder:
        if self._embedder is None:
            if self.prefer_bedrock:
                try:
                    embedder = BedrockEmbedder()
                    # Test connection
                    embedder.embed("test")
                    self._embedder = embedder
                    print("Using Bedrock Titan embeddings")
                except Exception as e:
                    print(f"Bedrock unavailable ({e}), falling back to Ollama")
                    self._embedder = OllamaEmbedder()
            else:
                self._embedder = OllamaEmbedder()
        return self._embedder
    
    @property
    def dimensions(self) -> int:
        return self.embedder.dimensions
    
    def embed(self, text: str) -> list[float]:
        return self.embedder.embed(text)
    
    def embed_batch(self, texts: Sequence[str], batch_size: int = 20) -> list[list[float]]:
        return self.embedder.embed_batch(texts, batch_size)


# Test
if __name__ == "__main__":
    print("Testing Bedrock Embedder...")
    
    try:
        embedder = BedrockEmbedder()
        
        test_texts = [
            "How do I restart an EKS deployment?",
            "kubectl rollout restart deployment",
            "The database connection is timing out"
        ]
        
        for text in test_texts:
            embedding = embedder.embed(text)
            print(f"\nText: {text[:50]}...")
            print(f"Embedding dimensions: {len(embedding)}")
            print(f"First 5 values: {embedding[:5]}")
        
        # Test similarity
        import numpy as np
        
        e1 = np.array(embedder.embed("restart kubernetes deployment"))
        e2 = np.array(embedder.embed("kubectl rollout restart"))
        e3 = np.array(embedder.embed("database connection error"))
        
        sim_12 = np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2))
        sim_13 = np.dot(e1, e3) / (np.linalg.norm(e1) * np.linalg.norm(e3))
        
        print(f"\nSimilarity (restart deployment vs kubectl rollout): {sim_12:.4f}")
        print(f"Similarity (restart deployment vs database error): {sim_13:.4f}")
        print("(Higher = more similar, expect first pair to be higher)")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have AWS credentials configured")
