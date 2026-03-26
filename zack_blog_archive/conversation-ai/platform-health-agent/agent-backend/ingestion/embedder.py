"""Embedder — convert text chunks to vector embeddings using AWS Bedrock Titan.

How embeddings work:
- Each chunk of text is sent to AWS Bedrock's Titan Embed V2 model
- The model returns a list of 1024 numbers (a "vector")
- These numbers represent the MEANING of the text
- Similar text → similar vectors → found by vector search

This is the bridge between human-readable text and machine-searchable vectors.
"""

import json
import time
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

# AWS configuration
AWS_PROFILE = os.getenv("AWS_PROFILE", "sandboxtest")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
EMBED_MODEL_ID = os.getenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS", "1024"))


def get_bedrock_client():
    """Create a Bedrock Runtime client using the configured AWS profile."""
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    return session.client("bedrock-runtime")


def embed_single(client, text: str) -> list[float]:
    """Embed a single text string using Bedrock Titan.
    
    Args:
        client: boto3 bedrock-runtime client
        text: The text to embed (will be truncated if too long)
    
    Returns:
        List of 1024 floats (the embedding vector)
    """
    # Titan Embed V2 has a max input of ~8000 tokens. Truncate if needed.
    if len(text) > 20000:
        text = text[:20000]

    body = json.dumps({
        "inputText": text,
        "dimensions": EMBED_DIMENSIONS,
    })

    response = client.invoke_model(
        modelId=EMBED_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    result = json.loads(response["body"].read())
    return result["embedding"]


def embed_chunks(chunks: list[dict], batch_size: int = 10) -> list[dict]:
    """Embed all chunks using Bedrock Titan.
    
    Adds an 'embedding' field (list of 1024 floats) to each chunk dict.
    
    Processes in batches to show progress and respect API limits.
    """
    client = get_bedrock_client()
    embedded = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        try:
            embedding = embed_single(client, chunk["content"])
            chunk["embedding"] = embedding
            embedded.append(chunk)

            # Progress update every 10 chunks
            if (i + 1) % batch_size == 0 or i == total - 1:
                print(f"   Embedded {i + 1}/{total} chunks...")

        except Exception as e:
            print(f"   ⚠️  Failed to embed chunk {i} ({chunk['source']}): {e}")
            # Skip this chunk rather than failing the whole pipeline
            continue

        # Small delay to avoid throttling (Bedrock has rate limits)
        if (i + 1) % batch_size == 0:
            time.sleep(0.5)

    return embedded
