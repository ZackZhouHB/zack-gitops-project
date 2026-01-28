# Product Catalog - Mac Mini LLM Appliance

## Hardware Tiers

| Tier | Mac Mini Model | Memory | Storage | Base Cost (AUD) |
|------|----------------|--------|---------|-----------------|
| Starter | M4 | 16GB | 256GB | ~$1,000 |
| Professional | M4 | 24GB | 512GB | ~$1,500 |
| Business | M4 Pro | 48GB | 512GB | ~$2,800 |
| Enterprise | M4 Pro | 64GB | 1TB | ~$3,500 |

---

## Tier 1: Starter (16GB)

### Best For
- Individual professionals
- Small teams (1-3 users)
- Basic Q&A, summarization, drafting

### Recommended Models

| Model | Size | Quantization | Context | Tokens/sec | Use Case |
|-------|------|--------------|---------|------------|----------|
| Llama 3.2 3B | 2GB | Q4_K_M | 128K | 80-100 | Fast responses, simple tasks |
| Phi-3 Mini | 2.3GB | Q4_K_M | 128K | 70-90 | Reasoning, coding assistance |
| Mistral 7B | 4GB | Q4_K_M | 32K | 40-50 | General purpose |
| Qwen2.5 7B | 4.5GB | Q4_K_M | 128K | 35-45 | Multilingual, coding |

### Limitations
- Single concurrent user recommended
- Not suitable for long documents (>10K tokens)
- Limited coding capability

### Pricing Suggestion
- Hardware + Setup: $1,800 - $2,200 AUD

---

## Tier 2: Professional (24GB)

### Best For
- Small business teams (3-8 users)
- Document analysis
- Code assistance
- Customer service drafts

### Recommended Models

| Model | Size | Quantization | Context | Tokens/sec | Use Case |
|-------|------|--------------|---------|------------|----------|
| Llama 3.1 8B | 4.7GB | Q4_K_M | 128K | 45-55 | Best balance for general use |
| Mistral Nemo 12B | 7GB | Q4_K_M | 128K | 30-40 | Strong reasoning |
| CodeLlama 13B | 7.4GB | Q4_K_M | 16K | 25-35 | Code generation |
| Qwen2.5 14B | 8.5GB | Q4_K_M | 128K | 25-30 | Advanced multilingual |
| DeepSeek Coder V2 Lite | 9GB | Q4_K_M | 128K | 20-28 | Coding specialist |

### Capabilities
- 2-3 concurrent users
- Document summarization up to 50 pages
- Code review and generation
- Email/report drafting

### Pricing Suggestion
- Hardware + Setup: $2,500 - $3,000 AUD

---

## Tier 3: Business (48GB)

### Best For
- Medium teams (8-20 users)
- Legal document review
- Technical documentation
- Research assistance

### Recommended Models

| Model | Size | Quantization | Context | Tokens/sec | Use Case |
|-------|------|--------------|---------|------------|----------|
| Llama 3.1 70B | 26GB | Q3_K_M | 128K | 12-18 | Near GPT-4 quality |
| Qwen2.5 32B | 19GB | Q4_K_M | 128K | 18-25 | Excellent reasoning |
| Mixtral 8x7B | 26GB | Q4_K_M | 32K | 15-22 | MoE efficiency |
| DeepSeek Coder 33B | 19GB | Q4_K_M | 16K | 15-20 | Enterprise coding |
| Yi-34B | 20GB | Q4_K_M | 200K | 14-18 | Long context specialist |

### Capabilities
- 5-8 concurrent users
- Complex reasoning tasks
- Full codebase analysis
- Legal/medical document review
- RAG with large knowledge bases

### Pricing Suggestion
- Hardware + Setup: $4,500 - $5,500 AUD

---

## Tier 4: Enterprise (64GB)

### Best For
- Large teams (20+ users)
- Mission-critical applications
- Maximum quality requirements
- Multi-model deployment

### Recommended Models

| Model | Size | Quantization | Context | Tokens/sec | Use Case |
|-------|------|--------------|---------|------------|----------|
| Llama 3.1 70B | 40GB | Q5_K_M | 128K | 10-15 | Highest quality general |
| Qwen2.5 72B | 42GB | Q4_K_M | 128K | 8-12 | Best multilingual |
| DeepSeek V2.5 | 45GB | Q4_K_M | 128K | 8-12 | Coding + reasoning |
| Command R+ | 40GB | Q4_K_M | 128K | 9-14 | RAG optimized |

### Multi-Model Setup Option
Run multiple specialized models simultaneously:
- Llama 3.1 8B (general queries) - 5GB
- DeepSeek Coder 33B (coding) - 19GB
- Qwen2.5 32B (documents) - 19GB
- Total: ~43GB, leaves headroom for context

### Capabilities
- 10-15 concurrent users
- Enterprise-grade quality
- Complex multi-step reasoning
- Full software development assistance
- Regulatory compliance documentation

### Pricing Suggestion
- Hardware + Setup: $6,000 - $7,500 AUD

---

## Use Case Matrix

| Use Case | Min Tier | Recommended Model | Why |
|----------|----------|-------------------|-----|
| Email drafting | Starter | Llama 3.2 3B | Fast, simple task |
| Meeting summaries | Starter | Phi-3 Mini | Good at extraction |
| Code review | Professional | CodeLlama 13B | Code-specialized |
| Legal contracts | Business | Llama 3.1 70B Q3 | Nuance required |
| Medical notes | Business | Qwen2.5 32B | Accuracy critical |
| Research papers | Business | Yi-34B | Long context |
| Full dev assistant | Enterprise | DeepSeek V2.5 | Complex reasoning |
| Customer support bot | Professional | Mistral Nemo 12B | Balance speed/quality |
| Translation | Professional | Qwen2.5 14B | Multilingual strength |
| Data analysis | Business | Mixtral 8x7B | Reasoning + speed |

---

## Quantization Guide

| Quantization | Quality Loss | Size Reduction | When to Use |
|--------------|--------------|----------------|-------------|
| Q8_0 | ~0.5% | 50% | Max quality, enough RAM |
| Q6_K | ~1% | 60% | High quality balance |
| Q5_K_M | ~2% | 65% | Recommended default |
| Q4_K_M | ~3-4% | 70% | Best size/quality ratio |
| Q3_K_M | ~5-8% | 75% | Fit larger models |
| Q2_K | ~10-15% | 80% | Last resort |

### Recommendation
- **Default**: Q4_K_M for most deployments
- **Quality-critical**: Q5_K_M or Q6_K
- **Fitting large models**: Q3_K_M acceptable

---

## Performance Expectations

### Tokens per Second by Hardware

| Model Size | 16GB M4 | 24GB M4 | 48GB M4 Pro | 64GB M4 Pro |
|------------|---------|---------|-------------|-------------|
| 3B Q4 | 80-100 | 90-110 | 100-120 | 100-120 |
| 7B Q4 | 40-50 | 45-55 | 55-65 | 55-65 |
| 13B Q4 | 20-28 | 25-35 | 35-45 | 35-45 |
| 32B Q4 | ❌ | ❌ | 18-25 | 20-28 |
| 70B Q4 | ❌ | ❌ | ❌ | 10-15 |
| 70B Q3 | ❌ | ❌ | 12-18 | 14-20 |

### User Experience Guidelines
- **>50 tok/s**: Feels instant, streaming smooth
- **30-50 tok/s**: Good experience, slight wait
- **15-30 tok/s**: Acceptable for complex tasks
- **<15 tok/s**: Best for batch/async workloads

---

## Add-On Services

| Service | Description | Price (AUD) |
|---------|-------------|-------------|
| Custom model fine-tuning | Train on customer data | $2,000+ |
| RAG setup | Document ingestion pipeline | $1,500 |
| SSO integration | LDAP/SAML configuration | $800 |
| On-site installation | Physical setup + training | $500 |
| Annual support | Updates, troubleshooting | $1,200/yr |
| Model updates | Quarterly model refreshes | $600/yr |

---

## Comparison vs Cloud

| Factor | Mac Mini LLM | Cloud LLM (GPT-4/Claude) |
|--------|--------------|--------------------------|
| Data privacy | ✅ 100% local | ❌ Data leaves network |
| Monthly cost | $0 after purchase | $20-100+/user/month |
| Internet required | ❌ No | ✅ Yes |
| Latency | <100ms local | 200-500ms typical |
| Customization | ✅ Full control | ❌ Limited |
| Quality (70B) | ~90% of GPT-4 | 100% baseline |
| Compliance | ✅ Easy | ⚠️ Requires review |

### Break-even Analysis
- 5 users @ $30/month cloud = $150/month = $1,800/year
- Professional tier pays for itself in ~18 months
- Business tier pays for itself in ~30 months (vs enterprise cloud)
