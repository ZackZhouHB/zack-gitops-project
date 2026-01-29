# Production LLM Platform: Beyond the Basics

> What separates a learning project from production-ready AI infrastructure

---

## Overview

The `bedrock_client.py` we built handles the happy path. Production systems must handle:
- Things going wrong (retries, failover)
- Things going expensive (caching, rate limiting)
- Things going invisible (observability)
- Things going slow (async)

---

## 1. Caching (Redis)

### The Problem

```
User A asks: "What is Amazon Bedrock?"     → $0.006
User B asks: "What is Amazon Bedrock?"     → $0.006  (same question!)
User C asks: "What is Amazon Bedrock?"     → $0.006  (same question!)
...
1000 users ask the same thing              → $6.00
```

### The Solution

```
User A asks: "What is Amazon Bedrock?"     → $0.006 (cache miss, call Bedrock)
User B asks: "What is Amazon Bedrock?"     → $0.000 (cache hit, return cached)
User C asks: "What is Amazon Bedrock?"     → $0.000 (cache hit)
...
1000 users ask the same thing              → $0.006 total
```

### How It Works

```
┌──────────┐     ┌─────────┐     ┌─────────┐
│  Request │────▶│  Redis  │────▶│ Bedrock │
└──────────┘     │ (cache) │     └─────────┘
                 └────┬────┘
                      │
            Cache hit? Return immediately
            Cache miss? Call Bedrock, store result
```

### Implementation Pattern

```python
import hashlib
import redis

class CachedBedrockClient(BedrockClient):
    def __init__(self, redis_url: str = "redis://localhost:6379", ttl: int = 3600):
        super().__init__()
        self.redis = redis.from_url(redis_url)
        self.ttl = ttl  # Cache for 1 hour
    
    def _cache_key(self, prompt: str, model: Model) -> str:
        """Create deterministic cache key from prompt + model."""
        content = f"{model.value}:{prompt}"
        return f"llm:{hashlib.sha256(content.encode()).hexdigest()}"
    
    def invoke(self, prompt: str, model: Model = Model.HAIKU, **kwargs):
        cache_key = self._cache_key(prompt, model)
        
        # Check cache first
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached), Usage(0, 0, model, 0)  # Zero cost!
        
        # Cache miss - call Bedrock
        response, usage = super().invoke(prompt, model, **kwargs)
        
        # Store in cache
        self.redis.setex(cache_key, self.ttl, json.dumps(response))
        
        return response, usage
```

### When to Use

| Use Case | Cache? | Why |
|----------|--------|-----|
| FAQ bot | ✅ Yes | Same questions repeated |
| Document Q&A | ⚠️ Maybe | Same doc, different questions |
| Creative writing | ❌ No | Want different outputs |
| Personalized responses | ❌ No | Context varies per user |

### AWS Options for Caching

| Service | Use When |
|---------|----------|
| ElastiCache (Redis) | Low latency, simple key-value |
| DynamoDB + DAX | Need persistence, complex queries |
| Lambda response caching | API Gateway level, simple cases |

---

## 2. Retry Logic with Exponential Backoff

### The Problem

Bedrock (and all cloud APIs) will throttle you:

```
Request 1: ✅ Success
Request 2: ✅ Success
Request 3: ❌ ThrottlingException - Rate exceeded
Request 4: ❌ ThrottlingException
...
```

Without retry logic, your app crashes. With naive retry, you make it worse:

```python
# BAD - hammers the API, makes throttling worse
while True:
    try:
        response = client.invoke_model(...)
        break
    except ThrottlingException:
        continue  # Immediately retry = more throttling
```

### The Solution: Exponential Backoff

```
Attempt 1: Failed  → Wait 1 second
Attempt 2: Failed  → Wait 2 seconds
Attempt 3: Failed  → Wait 4 seconds
Attempt 4: Failed  → Wait 8 seconds
Attempt 5: Success!
```

### Implementation Pattern

```python
import time
import random
from botocore.exceptions import ClientError

def invoke_with_retry(
    self, 
    prompt: str, 
    model: Model = Model.HAIKU,
    max_retries: int = 5,
    base_delay: float = 1.0
):
    """Invoke with exponential backoff and jitter."""
    
    for attempt in range(max_retries):
        try:
            return self.invoke(prompt, model)
        
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            
            # Only retry on throttling/transient errors
            if error_code not in ["ThrottlingException", "ServiceUnavailableException"]:
                raise  # Don't retry on bad request, auth errors, etc.
            
            if attempt == max_retries - 1:
                raise  # Final attempt failed
            
            # Exponential backoff with jitter
            delay = base_delay * (2 ** attempt)
            jitter = random.uniform(0, delay * 0.1)  # Add 0-10% randomness
            
            print(f"Throttled. Retrying in {delay + jitter:.1f}s (attempt {attempt + 1}/{max_retries})")
            time.sleep(delay + jitter)
    
    raise Exception("Max retries exceeded")
```

### Why Jitter?

Without jitter, if 100 requests fail at the same time:
```
All 100 retry at exactly 1 second  → All fail again
All 100 retry at exactly 2 seconds → All fail again
```

With jitter:
```
Request 1 retries at 1.03s
Request 2 retries at 1.07s
Request 3 retries at 0.98s
...spread out, less thundering herd
```

### AWS SDK Built-in Retry

boto3 has built-in retry, but you may want custom logic:

```python
from botocore.config import Config

# Use boto3's built-in retry
config = Config(
    retries={
        'max_attempts': 5,
        'mode': 'adaptive'  # Adjusts based on throttling
    }
)
client = boto3.client('bedrock-runtime', config=config)
```

---

## 3. Async Support

### The Problem

Synchronous code blocks while waiting:

```python
# Sync - each call waits for previous to complete
for user in users:
    response = client.invoke(user.question)  # Blocks 2 seconds
    # 100 users = 200 seconds total
```

### The Solution

Async code runs concurrently:

```python
# Async - all calls run in parallel
responses = await asyncio.gather(*[
    client.invoke_async(user.question) for user in users
])
# 100 users = ~2 seconds total (parallel)
```

### Implementation Pattern

```python
import asyncio
import aioboto3  # pip install aioboto3

class AsyncBedrockClient:
    def __init__(self, region: str = REGION):
        self.region = region
        self.session = aioboto3.Session()
    
    async def invoke_async(self, prompt: str, model: Model = Model.HAIKU, max_tokens: int = 1024):
        """Non-blocking async invocation."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        async with self.session.client("bedrock-runtime", region_name=self.region) as client:
            response = await client.invoke_model(
                modelId=model.value,
                body=json.dumps(body)
            )
            result = json.loads(await response["body"].read())
            return result["content"][0]["text"]

# Usage
async def process_batch(questions: list[str]):
    client = AsyncBedrockClient()
    tasks = [client.invoke_async(q) for q in questions]
    return await asyncio.gather(*tasks)

# Run
responses = asyncio.run(process_batch(["Q1", "Q2", "Q3", ...]))
```

### When to Use Async

| Scenario | Sync or Async? |
|----------|----------------|
| CLI tool, one query | Sync (simpler) |
| Web API handling many users | Async |
| Batch processing 1000 docs | Async |
| Lambda (single request) | Sync (Lambda handles concurrency) |

### Concurrency Limits

Don't go crazy - Bedrock has rate limits:

```python
# BAD - 1000 concurrent requests = instant throttling
await asyncio.gather(*[invoke(q) for q in questions])

# GOOD - limit concurrency
semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

async def limited_invoke(question):
    async with semaphore:
        return await client.invoke_async(question)

await asyncio.gather(*[limited_invoke(q) for q in questions])
```

---

## 4. Observability (Tracing & Metrics)

### The Problem

Without observability:
- "Why is the chatbot slow?" → 🤷
- "Which model is being used most?" → 🤷
- "Where is the latency coming from?" → 🤷

### The Solution

Instrument everything:

```
Request → [Trace ID: abc123]
  ├── Cache lookup: 2ms
  ├── Bedrock call: 1,847ms
  │     ├── Model: claude-3-haiku
  │     ├── Input tokens: 150
  │     └── Output tokens: 89
  └── Total: 1,849ms
```

### Implementation Pattern (OpenTelemetry)

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Setup tracer
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Export to X-Ray, Jaeger, etc.
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter())
)

class ObservableBedrockClient(BedrockClient):
    def invoke(self, prompt: str, model: Model = Model.HAIKU, **kwargs):
        with tracer.start_as_current_span("bedrock.invoke") as span:
            # Add attributes for filtering/searching
            span.set_attribute("llm.model", model.value)
            span.set_attribute("llm.prompt_length", len(prompt))
            
            response, usage = super().invoke(prompt, model, **kwargs)
            
            # Add result attributes
            span.set_attribute("llm.input_tokens", usage.input_tokens)
            span.set_attribute("llm.output_tokens", usage.output_tokens)
            span.set_attribute("llm.latency_ms", usage.latency_ms)
            span.set_attribute("llm.cost_usd", usage.cost_usd)
            
            return response, usage
```

### CloudWatch Metrics Pattern

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def emit_metrics(usage: Usage):
    cloudwatch.put_metric_data(
        Namespace='LLMPlatform',
        MetricData=[
            {
                'MetricName': 'TokensUsed',
                'Value': usage.input_tokens + usage.output_tokens,
                'Unit': 'Count',
                'Dimensions': [
                    {'Name': 'Model', 'Value': usage.model.name},
                ]
            },
            {
                'MetricName': 'InvocationLatency',
                'Value': usage.latency_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {'Name': 'Model', 'Value': usage.model.name},
                ]
            },
            {
                'MetricName': 'CostUSD',
                'Value': usage.cost_usd,
                'Unit': 'None',
                'Dimensions': [
                    {'Name': 'Model', 'Value': usage.model.name},
                ]
            }
        ]
    )
```

### What to Monitor

| Metric | Alert Threshold | Why |
|--------|-----------------|-----|
| Latency p99 | > 5 seconds | User experience |
| Error rate | > 1% | Service health |
| Daily cost | > $X | Budget control |
| Throttling count | > 10/min | Need to scale or optimize |
| Cache hit rate | < 50% | Cache not effective |

---

## 5. Rate Limiting

### The Problem

One bad actor (or bug) can burn your entire budget:

```
Normal user: 10 queries/day
Buggy script: 10,000 queries/hour → $600 bill
```

### The Solution

Limit requests per user/API key:

```
User A: 100 requests/hour allowed
User A makes request 101 → HTTP 429 Too Many Requests
```

### Implementation Pattern (Token Bucket)

```python
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.buckets = defaultdict(list)  # user_id -> [timestamps]
    
    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        
        # Remove old timestamps
        self.buckets[user_id] = [
            ts for ts in self.buckets[user_id] if ts > minute_ago
        ]
        
        # Check limit
        if len(self.buckets[user_id]) >= self.rpm:
            return False
        
        # Record this request
        self.buckets[user_id].append(now)
        return True

class RateLimitedBedrockClient(BedrockClient):
    def __init__(self, rpm: int = 60):
        super().__init__()
        self.limiter = RateLimiter(rpm)
    
    def invoke(self, prompt: str, user_id: str, **kwargs):
        if not self.limiter.is_allowed(user_id):
            raise RateLimitExceeded(f"User {user_id} exceeded {self.limiter.rpm} requests/minute")
        
        return super().invoke(prompt, **kwargs)
```

### AWS Options for Rate Limiting

| Service | Use When |
|---------|----------|
| API Gateway throttling | Per-API-key limits, simple setup |
| WAF rate rules | IP-based limiting |
| ElastiCache (Redis) | Distributed rate limiting across Lambda instances |
| DynamoDB | Persistent quotas (monthly limits) |

### Tiered Rate Limits (Real-World)

```python
TIER_LIMITS = {
    "free": {"rpm": 10, "daily_tokens": 10_000},
    "pro": {"rpm": 100, "daily_tokens": 100_000},
    "enterprise": {"rpm": 1000, "daily_tokens": 1_000_000},
}

def get_user_tier(user_id: str) -> str:
    # Look up in database
    return "pro"

def check_limits(user_id: str, tokens_requested: int):
    tier = get_user_tier(user_id)
    limits = TIER_LIMITS[tier]
    # Check both RPM and daily token limits
    ...
```

---

## 6. Multi-Region Failover

### The Problem

AWS regions can have issues:
- ap-southeast-2 has outage → Your app is down
- ap-southeast-2 is throttling → Requests fail

### The Solution

Failover to another region:

```
Primary: ap-southeast-2
         ↓ (fails)
Fallback: us-east-1
```

### Implementation Pattern

```python
REGIONS = ["ap-southeast-2", "us-east-1", "eu-west-1"]

class MultiRegionBedrockClient:
    def __init__(self):
        self.clients = {
            region: boto3.Session(region_name=region).client("bedrock-runtime")
            for region in REGIONS
        }
        self.primary = REGIONS[0]
    
    def invoke(self, prompt: str, model: Model = Model.HAIKU, **kwargs):
        errors = []
        
        # Try primary first, then fallbacks
        for region in REGIONS:
            try:
                client = self.clients[region]
                response = client.invoke_model(
                    modelId=model.value,
                    body=json.dumps({...})
                )
                
                if region != self.primary:
                    print(f"Warning: Using fallback region {region}")
                
                return self._parse_response(response)
            
            except ClientError as e:
                errors.append((region, e))
                continue  # Try next region
        
        # All regions failed
        raise AllRegionsFailedError(errors)
```

### Health Check Pattern

Don't wait for failure - proactively check health:

```python
import threading
import time

class HealthCheckedBedrockClient:
    def __init__(self):
        self.region_health = {region: True for region in REGIONS}
        self._start_health_checker()
    
    def _start_health_checker(self):
        def check_loop():
            while True:
                for region in REGIONS:
                    try:
                        # Lightweight health check
                        client = self.clients[region]
                        client.invoke_model(
                            modelId=Model.HAIKU.value,
                            body=json.dumps({"anthropic_version": "bedrock-2023-05-31", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]})
                        )
                        self.region_health[region] = True
                    except:
                        self.region_health[region] = False
                
                time.sleep(60)  # Check every minute
        
        thread = threading.Thread(target=check_loop, daemon=True)
        thread.start()
    
    def get_healthy_region(self) -> str:
        for region in REGIONS:
            if self.region_health[region]:
                return region
        raise NoHealthyRegionError()
```

### Considerations

| Factor | Impact |
|--------|--------|
| Data residency | Some data can't leave certain regions (GDPR, etc.) |
| Latency | us-east-1 from Australia = +200ms |
| Cost | Some regions are more expensive |
| Model availability | Not all models in all regions |

---

## Summary: Production Checklist

Before going to production, ensure you have:

| Feature | Status | Priority |
|---------|--------|----------|
| ✅ Basic invocation | Done | Must have |
| ✅ Streaming | Done | Must have for chat |
| ✅ Guardrails | Done | Must have for enterprise |
| ✅ Cost tracking | Done | Must have |
| ✅ Model routing | Done | Should have |
| ⬜ Caching | TODO | Should have (cost savings) |
| ⬜ Retry logic | TODO | Must have |
| ⬜ Async support | TODO | Depends on use case |
| ⬜ Observability | TODO | Must have |
| ⬜ Rate limiting | TODO | Must have for multi-tenant |
| ⬜ Multi-region | TODO | Nice to have |

---

## Next Steps

1. **Week 2:** Add LangChain with DynamoDB memory (persistence pattern)
2. **Week 3:** Build RAG with caching and observability
3. **Week 4:** Full platform with all production features

Want to implement any of these features now, or continue with the learning path?
