"""
Unified LLM Client - Bedrock + Ollama
=====================================
Week 1 Deliverable: Switch between AWS Bedrock and remote Ollama with one config change.

WHY THIS MATTERS:
- Development: Use free local Ollama (your RTX 5070 Ti) for iteration
- Production: Switch to Bedrock for managed, scalable inference
- Cost: Ollama = $0, Bedrock = pay per token
- Privacy: Ollama keeps data on your network, Bedrock sends to AWS

USAGE:
    # Use Ollama (default for dev)
    client = LLMClient(backend="ollama")
    
    # Use Bedrock (for prod/testing)
    client = LLMClient(backend="bedrock")
    
    # Or set via environment variable
    export LLM_BACKEND=bedrock
    client = LLMClient()
"""

import os
import json
import requests
import boto3
from dataclasses import dataclass
from enum import Enum
from typing import Generator, Optional

# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class OllamaConfig:
    """Remote Ollama server (your Windows PC with RTX 5070 Ti)"""
    host: str = "192.168.50.61"
    port: int = 11434
    model: str = "gpt-oss-gpu:latest"  # Your 20.9B model
    
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class BedrockConfig:
    """AWS Bedrock configuration"""
    region: str = "ap-southeast-2"
    profile: str = "default"
    model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"


class Backend(Enum):
    OLLAMA = "ollama"
    BEDROCK = "bedrock"


# ============================================================================
# LLM CLIENT
# ============================================================================

class LLMClient:
    """
    Unified interface for LLM inference.
    
    Abstracts away the backend so your application code doesn't change
    whether you're using local Ollama or AWS Bedrock.
    """
    
    def __init__(
        self,
        backend: Optional[str] = None,
        ollama_config: Optional[OllamaConfig] = None,
        bedrock_config: Optional[BedrockConfig] = None,
    ):
        # Priority: explicit param > env var > default (ollama)
        backend_str = backend or os.getenv("LLM_BACKEND", "ollama")
        self.backend = Backend(backend_str.lower())
        
        self.ollama = ollama_config or OllamaConfig()
        self.bedrock = bedrock_config or BedrockConfig()
        
        # Initialize Bedrock client lazily (only if needed)
        self._bedrock_client = None
    
    @property
    def bedrock_client(self):
        """Lazy initialization of Bedrock client."""
        if self._bedrock_client is None:
            session = boto3.Session(
                profile_name=self.bedrock.profile,
                region_name=self.bedrock.region
            )
            self._bedrock_client = session.client("bedrock-runtime")
        return self._bedrock_client
    
    def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The input text
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated text response
        """
        if self.backend == Backend.OLLAMA:
            return self._generate_ollama(prompt, max_tokens)
        else:
            return self._generate_bedrock(prompt, max_tokens)
    
    def _generate_ollama(self, prompt: str, max_tokens: int) -> str:
        """Call remote Ollama server."""
        url = f"{self.ollama.base_url}/api/generate"
        payload = {
            "model": self.ollama.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens}
        }
        
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["response"]
    
    def _generate_bedrock(self, prompt: str, max_tokens: int) -> str:
        """Call AWS Bedrock."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = self.bedrock_client.invoke_model(
            modelId=self.bedrock.model,
            body=json.dumps(body)
        )
        
        result = json.loads(response["body"].read())
        return result["content"][0]["text"]
    
    def stream(self, prompt: str, max_tokens: int = 1024) -> Generator[str, None, None]:
        """
        Stream response tokens as they're generated.
        
        Yields:
            Text chunks as they arrive
        """
        if self.backend == Backend.OLLAMA:
            yield from self._stream_ollama(prompt, max_tokens)
        else:
            yield from self._stream_bedrock(prompt, max_tokens)
    
    def _stream_ollama(self, prompt: str, max_tokens: int) -> Generator[str, None, None]:
        """Stream from Ollama."""
        url = f"{self.ollama.base_url}/api/generate"
        payload = {
            "model": self.ollama.model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_predict": max_tokens}
        }
        
        with requests.post(url, json=payload, stream=True, timeout=120) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
    
    def _stream_bedrock(self, prompt: str, max_tokens: int) -> Generator[str, None, None]:
        """Stream from Bedrock."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = self.bedrock_client.invoke_model_with_response_stream(
            modelId=self.bedrock.model,
            body=json.dumps(body)
        )
        
        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            if chunk["type"] == "content_block_delta":
                yield chunk["delta"].get("text", "")
    
    def health_check(self) -> dict:
        """Check if the backend is reachable."""
        if self.backend == Backend.OLLAMA:
            try:
                response = requests.get(f"{self.ollama.base_url}/api/tags", timeout=5)
                models = [m["name"] for m in response.json().get("models", [])]
                return {"status": "ok", "backend": "ollama", "models": models}
            except Exception as e:
                return {"status": "error", "backend": "ollama", "error": str(e)}
        else:
            try:
                # Simple test - use bedrock (not runtime) to list models
                session = boto3.Session(profile_name=self.bedrock.profile, region_name=self.bedrock.region)
                bedrock = session.client("bedrock")
                bedrock.list_foundation_models(byOutputModality="TEXT")
                return {"status": "ok", "backend": "bedrock", "region": self.bedrock.region}
            except Exception as e:
                return {"status": "error", "backend": "bedrock", "error": str(e)}


# ============================================================================
# CLI DEMO
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test LLM backends")
    parser.add_argument("--backend", "-b", choices=["ollama", "bedrock"], default="ollama")
    parser.add_argument("--prompt", "-p", default="Explain Kubernetes in one sentence.")
    parser.add_argument("--stream", "-s", action="store_true", help="Stream output")
    parser.add_argument("--health", action="store_true", help="Health check only")
    args = parser.parse_args()
    
    client = LLMClient(backend=args.backend)
    
    if args.health:
        print(f"Health check ({args.backend}):")
        print(json.dumps(client.health_check(), indent=2))
    elif args.stream:
        print(f"[{args.backend}] Streaming response:\n")
        for chunk in client.stream(args.prompt):
            print(chunk, end="", flush=True)
        print()
    else:
        print(f"[{args.backend}] Generating response...\n")
        response = client.generate(args.prompt)
        print(response)
