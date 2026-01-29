"""
Enterprise Bedrock Client Module
================================
A production-ready wrapper for AWS Bedrock that handles:
- Sync + Streaming invocation
- Multi-model routing (Haiku for simple, Sonnet for complex)
- Cost tracking per request and session
- Guardrails for PII protection
- Rate limiting for multi-tenant apps
- Retry logic with exponential backoff

This is the kind of internal SDK that AI platform teams build
before any application code. Product teams then import this
instead of calling boto3 directly.
"""

# ============================================================================
# IMPORTS
# ============================================================================
import json                          # Bedrock API uses JSON for request/response
import time                          # Measure latency, implement delays
import random                        # Add jitter to retry delays
from dataclasses import dataclass    # Clean data structures (Python 3.7+)
from enum import Enum                # Type-safe constants, prevents typos
from typing import Generator         # Type hint for streaming function
from collections import defaultdict  # Auto-create empty lists for rate limiter
import boto3                         # AWS SDK for Python
from botocore.exceptions import ClientError  # Catch AWS API errors

# ============================================================================
# CONFIGURATION
# ============================================================================
REGION = "ap-southeast-2"
PROFILE = "default"

# ============================================================================
# MODEL DEFINITIONS
# Why Enum? If you typo the model ID string, you get a runtime error.
# With Enum, your IDE catches it immediately + provides autocomplete.
# ============================================================================
class Model(Enum):
    HAIKU = "anthropic.claude-3-haiku-20240307-v1:0"      # Fast, cheap ($0.25/1M input)
    SONNET = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Powerful ($3/1M input)

# ============================================================================
# GUARDRAIL CONFIG
# Guardrails filter PII, toxic content, etc. Create one in your AWS account:
#   aws bedrock create-guardrail --name "my-guardrail" --blocked-input-messaging "..." ...
# Then paste the ID here.
# ============================================================================
GUARDRAIL_ID = None
GUARDRAIL_VERSION = None

# ============================================================================
# PRICING
# Why track in code? Calculate cost per request, set budget alerts,
# generate reports for finance team. Prices are per 1K tokens.
# ============================================================================
PRICING = {
    Model.HAIKU: {"input": 0.00025, "output": 0.00125},   # 12x cheaper than Sonnet
    Model.SONNET: {"input": 0.003, "output": 0.015},
}


# ============================================================================
# RATE LIMITING
# ============================================================================
class RateLimitExceeded(Exception):
    """Raised when user exceeds their rate limit."""
    pass


class RateLimiter:
    """
    Token Bucket Rate Limiter
    =========================
    
    WHY THIS EXISTS:
    - Prevents single user/bug from burning your entire LLM budget
    - Enables tiered pricing (free: 10 rpm, pro: 100 rpm, enterprise: 1000 rpm)
    - Required for any multi-tenant SaaS platform
    
    HOW IT WORKS (Token Bucket Algorithm):
    - Track timestamps of each request per user
    - If requests in last 60 seconds >= limit, reject
    - Old timestamps automatically expire
    
    EXAMPLE:
        limiter = RateLimiter(requests_per_minute=10)
        limiter.check("user_123")  # ✅ Allowed (1/10)
        limiter.check("user_123")  # ✅ Allowed (2/10)
        ... 8 more times ...
        limiter.check("user_123")  # ❌ RateLimitExceeded
    """
    
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        # defaultdict auto-creates empty list when key doesn't exist
        # Without it: if user_id not in self.buckets: self.buckets[user_id] = []
        self.buckets: dict[str, list[float]] = defaultdict(list)
    
    def check(self, user_id: str) -> bool:
        """
        Check if user is within rate limit.
        Returns True if allowed, raises RateLimitExceeded if not.
        """
        now = time.time()
        minute_ago = now - 60
        
        # Clean up: remove timestamps older than 1 minute
        # This is the "sliding window" - only count recent requests
        self.buckets[user_id] = [ts for ts in self.buckets[user_id] if ts > minute_ago]
        
        # Check if at limit
        if len(self.buckets[user_id]) >= self.rpm:
            # Calculate how long until oldest request expires
            wait_time = 60 - (now - self.buckets[user_id][0])
            raise RateLimitExceeded(
                f"User '{user_id}' exceeded {self.rpm} requests/minute. "
                f"Wait {wait_time:.0f}s"
            )
        
        # Record this request
        self.buckets[user_id].append(now)
        return True


# ============================================================================
# USAGE TRACKING
# ============================================================================
@dataclass
class Usage:
    """
    Tracks token usage and cost for a single LLM call.
    
    WHY A DATACLASS?
    - Groups related data together cleanly
    - Auto-generates __init__, __repr__, __eq__
    - @property computes cost on-demand (always fresh)
    
    REAL-WORLD USE:
    - Log to CloudWatch for monitoring
    - Store in DynamoDB for billing/chargeback
    - Aggregate for cost dashboards
    """
    input_tokens: int      # Tokens in your prompt
    output_tokens: int     # Tokens in the response
    model: Model           # Which model was used
    latency_ms: float      # How long the call took

    @property
    def cost_usd(self) -> float:
        """Calculate cost based on model pricing. Computed on access, not stored."""
        p = PRICING[self.model]
        return (self.input_tokens * p["input"] + self.output_tokens * p["output"]) / 1000


# ============================================================================
# MAIN CLIENT CLASS
# ============================================================================
class BedrockClient:
    """
    Enterprise-ready Bedrock client with production features.
    
    BASIC USAGE:
        client = BedrockClient()
        response, usage = client.invoke("What is AWS?")
        print(f"Cost: ${usage.cost_usd}")
    
    MULTI-TENANT USAGE:
        client = BedrockClient(rate_limit_rpm=100)
        response, usage = client.invoke_for_user("What is AWS?", user_id="customer_123")
    
    WITH RETRY:
        response, usage = client.invoke_with_retry("What is AWS?", max_retries=5)
    """
    
    def __init__(self, profile: str = PROFILE, region: str = REGION, rate_limit_rpm: int = 60):
        """
        Initialize the client.
        
        WHY boto3.Session instead of boto3.client directly?
        - Explicit profile/region (important for multi-account setups)
        - Can switch between dev/prod accounts easily
        
        WHY bedrock-runtime (not bedrock)?
        - bedrock = Management API (list models, create guardrails)
        - bedrock-runtime = Inference API (invoke models) ← this is what we need
        """
        session = boto3.Session(profile_name=profile, region_name=region)
        self.client = session.client("bedrock-runtime")
        self.total_usage: list[Usage] = []  # Track all calls for session cost
        self.rate_limiter = RateLimiter(rate_limit_rpm)

    # ------------------------------------------------------------------------
    # RATE-LIMITED INVOKE (for multi-tenant apps)
    # ------------------------------------------------------------------------
    def invoke_for_user(
        self,
        prompt: str,
        user_id: str,
        model: Model = Model.HAIKU,
        max_tokens: int = 1024
    ) -> tuple[str, Usage]:
        """
        Rate-limited invoke for multi-tenant apps.
        
        USE THIS WHEN:
        - Building SaaS with multiple customers
        - Need to enforce per-user quotas
        - Protecting against runaway scripts or abuse
        
        EXAMPLE:
            # Free tier user - will be blocked after 10 requests/minute
            client = BedrockClient(rate_limit_rpm=10)
            response = client.invoke_for_user(prompt, user_id="free_user_123")
        """
        self.rate_limiter.check(user_id)  # Raises RateLimitExceeded if over limit
        return self.invoke(prompt, model, max_tokens)

    # ------------------------------------------------------------------------
    # BASIC INVOKE (synchronous)
    # ------------------------------------------------------------------------
    def invoke(
        self, 
        prompt: str, 
        model: Model = Model.HAIKU, 
        max_tokens: int = 1024, 
        use_guardrail: bool = False
    ) -> tuple[str, Usage]:
        """
        Synchronous invocation with cost tracking and optional guardrails.
        
        THE REQUEST BODY:
        - anthropic_version: Required by Claude, specifies API version
        - max_tokens: Limit output length (controls cost + prevents runaway)
        - messages: Chat format with roles (user/assistant/system)
        
        WHY MESSAGES FORMAT (not just a string)?
        - Supports multi-turn conversations
        - Can include system prompts
        - Industry standard (OpenAI, Anthropic, Google all use this)
        """
        # Build the request body (Claude's Messages API format)
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        start = time.time()
        
        # Build kwargs dynamically - cleaner than if/else for optional params
        kwargs = {"modelId": model.value, "body": json.dumps(body)}
        if use_guardrail and GUARDRAIL_ID:
            kwargs["guardrailIdentifier"] = GUARDRAIL_ID
            kwargs["guardrailVersion"] = GUARDRAIL_VERSION
        
        # Make the API call
        response = self.client.invoke_model(**kwargs)
        latency = (time.time() - start) * 1000

        # Parse response
        result = json.loads(response["body"].read())
        text = result["content"][0]["text"]
        
        # Track usage for cost monitoring
        usage = Usage(
            input_tokens=result["usage"]["input_tokens"],
            output_tokens=result["usage"]["output_tokens"],
            model=model,
            latency_ms=latency
        )
        self.total_usage.append(usage)
        
        return text, usage

    # ------------------------------------------------------------------------
    # STREAMING INVOKE (for chat UIs)
    # ------------------------------------------------------------------------
    def invoke_stream(
        self, 
        prompt: str, 
        model: Model = Model.SONNET, 
        max_tokens: int = 1024
    ) -> Generator[str, None, Usage]:
        """
        Streaming invocation - yields text chunks as they arrive.
        
        WHY STREAMING?
        - LLMs generate tokens one at a time
        - Without streaming: user waits 5-10 seconds, then sees wall of text
        - With streaming: user sees words appear in real-time (like ChatGPT)
        
        WHY GENERATOR (yield)?
        - Memory efficient - don't buffer entire response
        - Caller can process/display chunks immediately
        - Can be cancelled mid-stream if needed
        
        USAGE:
            for chunk in client.invoke_stream("Tell me a story"):
                print(chunk, end="", flush=True)  # Print as it arrives
        """
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        start = time.time()
        response = self.client.invoke_model_with_response_stream(
            modelId=model.value, 
            body=json.dumps(body)
        )

        # Track tokens from stream events
        input_tokens = output_tokens = 0
        
        # Process stream events as they arrive
        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            
            # Different event types carry different data
            if chunk["type"] == "content_block_delta":
                # This is actual text content - yield it to caller
                yield chunk["delta"]["text"]
            elif chunk["type"] == "message_delta":
                # End of message - contains output token count
                output_tokens = chunk["usage"]["output_tokens"]
            elif chunk["type"] == "message_start":
                # Start of message - contains input token count
                input_tokens = chunk["message"]["usage"]["input_tokens"]

        # Track usage after stream completes
        latency = (time.time() - start) * 1000
        usage = Usage(
            input_tokens=input_tokens, 
            output_tokens=output_tokens, 
            model=model, 
            latency_ms=latency
        )
        self.total_usage.append(usage)
        return usage

    # ------------------------------------------------------------------------
    # SMART ROUTING (cost optimization)
    # ------------------------------------------------------------------------
    def smart_route(self, prompt: str, max_tokens: int = 1024) -> tuple[str, Usage]:
        """
        Route to appropriate model based on task complexity.
        
        WHY ROUTE BETWEEN MODELS?
        - Sonnet is 12x more expensive than Haiku
        - Simple tasks don't need expensive models
        - Can save 60%+ on LLM costs with smart routing
        
        THIS IS A SIMPLE HEURISTIC. Production systems use:
        - ML classifier to detect task complexity
        - User tier (free → Haiku, premium → Sonnet)
        - Fallback chains (try Haiku, if bad → retry Sonnet)
        - A/B testing to measure quality difference
        """
        # Simple heuristic: short prompts + simple task keywords → Haiku
        simple_keywords = ["summarize", "translate", "list", "extract", "yes or no"]
        is_simple = len(prompt) < 500 or any(kw in prompt.lower() for kw in simple_keywords)
        
        model = Model.HAIKU if is_simple else Model.SONNET
        return self.invoke(prompt, model=model, max_tokens=max_tokens)

    # ------------------------------------------------------------------------
    # COST TRACKING
    # ------------------------------------------------------------------------
    def get_total_cost(self) -> float:
        """Get total cost of all calls in this session."""
        return sum(u.cost_usd for u in self.total_usage)

    # ------------------------------------------------------------------------
    # RETRY WITH EXPONENTIAL BACKOFF (production resilience)
    # ------------------------------------------------------------------------
    def invoke_with_retry(
        self,
        prompt: str,
        model: Model = Model.HAIKU,
        max_tokens: int = 1024,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> tuple[str, Usage]:
        """
        Invoke with exponential backoff for handling throttling.
        
        THE PROBLEM WITHOUT RETRY:
            Request 1: ✅ Success
            Request 2: ✅ Success  
            Request 3: ❌ ThrottlingException → APP CRASHES
        
        THE PROBLEM WITH NAIVE RETRY:
            while True:
                try: response = invoke(...)
                except: continue  # Immediately retry → makes throttling WORSE
        
        THE SOLUTION - EXPONENTIAL BACKOFF:
            Attempt 1: ❌ Failed → Wait 1 second
            Attempt 2: ❌ Failed → Wait 2 seconds (doubled)
            Attempt 3: ❌ Failed → Wait 4 seconds (doubled again)
            Attempt 4: ✅ Success!
        
        WHY EXPONENTIAL (not linear)?
        - Quickly reduces pressure on overloaded system
        - Gives system time to recover
        - Industry standard (AWS, Google, etc. all recommend this)
        
        WHY JITTER (random delay)?
        - Prevents "thundering herd" problem
        - Without jitter: 100 requests fail, all retry at exactly 1 second → all fail again
        - With jitter: requests spread out, system can handle them
        """
        # Only retry these errors - don't retry auth errors, bad requests, etc.
        retryable_errors = [
            "ThrottlingException",        # Rate limited
            "ServiceUnavailableException", # Temporary outage
            "ModelStreamErrorException"    # Stream interrupted
        ]
        
        for attempt in range(max_retries):
            try:
                return self.invoke(prompt, model, max_tokens)
            
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                
                # Don't retry non-transient errors
                if error_code not in retryable_errors:
                    raise  # Auth errors, validation errors, etc. - won't fix themselves
                
                # Don't retry if this was the last attempt
                if attempt == max_retries - 1:
                    raise  # Give up, let caller handle it
                
                # Calculate delay with exponential backoff + jitter
                delay = base_delay * (2 ** attempt)      # 1, 2, 4, 8, 16...
                jitter = random.uniform(0, delay * 0.1)  # Add 0-10% randomness
                total_delay = delay + jitter
                
                print(f"⚠️  {error_code}. Retry {attempt + 1}/{max_retries} in {total_delay:.1f}s")
                time.sleep(total_delay)
        
        # Should never reach here, but just in case
        raise Exception("Unexpected: should not reach here")

    # ------------------------------------------------------------------------
    # COST ESTIMATION (capacity planning)
    # ------------------------------------------------------------------------
    @staticmethod
    def estimate_workload_cost(
        queries_per_day: int,
        avg_input_tokens: int = 500,
        avg_output_tokens: int = 300,
        model: Model = Model.HAIKU,
        days: int = 30
    ) -> dict:
        """
        Estimate costs for a workload - useful for capacity planning.
        
        WHY @staticmethod?
        - Doesn't need self (no instance state)
        - Can call without creating client: BedrockClient.estimate_workload_cost(1000)
        
        REAL-WORLD USE:
        - PM asks: "How much will this feature cost at 10K users/day?"
        - You run: estimate_workload_cost(queries_per_day=10000)
        - Answer: "$50/day with Haiku, $600/day with Sonnet"
        """
        p = PRICING[model]
        daily_input_cost = (queries_per_day * avg_input_tokens * p["input"]) / 1000
        daily_output_cost = (queries_per_day * avg_output_tokens * p["output"]) / 1000
        daily_total = daily_input_cost + daily_output_cost
        
        return {
            "model": model.name,
            "queries_per_day": queries_per_day,
            "daily_cost_usd": round(daily_total, 2),
            "monthly_cost_usd": round(daily_total * days, 2),
            "cost_per_query_usd": round(daily_total / queries_per_day, 6)
        }


# ============================================================================
# DEMO / TEST CODE
# ============================================================================
if __name__ == "__main__":
    client = BedrockClient()

    # Task 1: Basic invoke
    print("=== Task 1: Basic Invoke (Haiku) ===")
    response, usage = client.invoke("What is Amazon Bedrock in one sentence?", model=Model.HAIKU)
    print(f"Response: {response}")
    print(f"Tokens: {usage.input_tokens} in / {usage.output_tokens} out | Cost: ${usage.cost_usd:.6f} | Latency: {usage.latency_ms:.0f}ms\n")

    # Task 2: Streaming
    print("=== Task 2: Streaming (Sonnet) ===")
    print("Response: ", end="", flush=True)
    stream = client.invoke_stream("Explain RAG architecture in 3 bullet points.", model=Model.SONNET)
    for chunk in stream:
        print(chunk, end="", flush=True)
    print(f"\n")

    # Task 5: Smart routing
    print("=== Task 5: Smart Routing ===")
    simple_q = "Translate 'hello' to French"
    complex_q = "Design a multi-tenant RAG system for a SaaS platform with row-level security. Include architecture diagram description."
    
    resp1, u1 = client.smart_route(simple_q)
    print(f"Simple Q -> {u1.model.name}: {resp1[:100]}...")
    
    resp2, u2 = client.smart_route(complex_q)
    print(f"Complex Q -> {u2.model.name}: {resp2[:100]}...")

    print(f"\n=== Total Session Cost: ${client.get_total_cost():.6f} ===")

    # Task 3: Guardrails - PII anonymization
    print("\n=== Task 3: Guardrails (PII Anonymization) ===")
    pii_prompt = "Summarize this: John Smith called from 555-123-4567 and his email is john@example.com"
    resp_no_guard, _ = client.invoke(pii_prompt, model=Model.HAIKU, use_guardrail=False)
    resp_with_guard, _ = client.invoke(pii_prompt, model=Model.HAIKU, use_guardrail=True)
    print(f"Without guardrail: {resp_no_guard[:150]}...")
    print(f"With guardrail: {resp_with_guard[:150]}...")

    # Task 4: Cost estimation for workload planning
    print("\n=== Task 4: Workload Cost Estimation ===")
    for model in [Model.HAIKU, Model.SONNET]:
        est = BedrockClient.estimate_workload_cost(queries_per_day=1000, model=model)
        print(f"{model.name}: ${est['daily_cost_usd']}/day, ${est['monthly_cost_usd']}/month ({est['cost_per_query_usd']}/query)")

    # === Production Features Demo ===
    
    # Rate Limiting Demo (no Bedrock call needed)
    print("\n=== Production Feature: Rate Limiting ===")
    limiter = RateLimiter(requests_per_minute=3)  # Low limit for demo
    
    for i in range(5):
        try:
            limiter.check("demo_user")
            print(f"  Request {i+1}: ✅ Allowed")
        except RateLimitExceeded as e:
            print(f"  Request {i+1}: ❌ {e}")
    
    # Retry Logic Demo (simulated - shows the pattern)
    print("\n=== Production Feature: Retry Logic ===")
    print("  Retry pattern: exponential backoff with jitter")
    print("  Attempt 1 fails → wait 1.0s")
    print("  Attempt 2 fails → wait 2.0s") 
    print("  Attempt 3 fails → wait 4.0s")
    print("  (In real use: invoke_with_retry() handles this automatically)")
    
    # Show what retry delays would look like
    base_delay = 1.0
    for attempt in range(3):
        delay = base_delay * (2 ** attempt)
        jitter = random.uniform(0, delay * 0.1)
        print(f"  Attempt {attempt+1} delay: {delay:.1f}s + {jitter:.2f}s jitter = {delay+jitter:.2f}s")
