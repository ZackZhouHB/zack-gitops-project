# Mac Mini LLM Appliance Catalog

This catalog maps Apple Silicon hardware specifications to appropriate Large Language Models (LLMs) and their corresponding business use cases. Use this to help clients select the right tier.

## Tier 1: The "Office Assistant"
**Hardware:** Mac Mini M4 (Base)
**Specs:** 24GB Unified Memory (Recommended minimum for future-proofing), 512GB SSD.
**Target Audience:** Small teams, individual executives, administrative roles.

| Component | Recommendation | Notes |
| :--- | :--- | :--- |
| **Model Size** | 7B - 9B Parameters | e.g., Llama 3.2 3B, Llama 3.1 8B, Gemma 2 9B |
| **Quantization** | Q4_K_M or Q5_K_M | Balances speed and accuracy. Uses ~5-7GB VRAM. |
| **Performance** | Very Fast (>50 tokens/sec) | Feels instantaneous. |
| **Use Cases** | • Email drafting & polishing<br>• Meeting summarization<br>• Basic RAG (chat with single PDF)<br>• English to [Language] translation |

---

## Tier 2: The "Knowledge Worker" (Most Popular)
**Hardware:** Mac Mini M4 Pro
**Specs:** 48GB or 64GB Unified Memory, 1TB SSD.
**Target Audience:** Legal teams, Developers, HR departments, Researchers.

| Component | Recommendation | Notes |
| :--- | :--- | :--- |
| **Model Size** | 14B - 32B Parameters | e.g., Qwen 2.5 32B, Mistral Small 24B, Codestral |
| **Quantization** | Q4_K_M | Uses ~18-22GB VRAM. Leaves ample room for OS + Context Window. |
| **Performance** | Fast (30-40 tokens/sec) | Smooth conversational flow. |
| **Use Cases** | • **Heavy RAG:** Search across hundreds of internal documents.<br>• **Coding:** Code generation and explanation.<br>• **Complex Logic:** Contract analysis, policy compliance checking. |

---

## Tier 3: The "Research Station"
**Hardware:** Mac Studio (M2/M4 Max/Ultra) or Mac Mini M4 Pro (64GB only if strictly managed)
**Specs:** 64GB - 128GB+ Unified Memory, 2TB SSD.
**Target Audience:** Data Scientists, Financial Analysts, specialized industries (Medical/Bio).

| Component | Recommendation | Notes |
| :--- | :--- | :--- |
| **Model Size** | 70B - 100B+ Parameters | e.g., Llama 3.3 70B, DeepSeek R1 (Distill or Full) |
| **Quantization** | Q3_K_M or Q4_K_M | 70B @ Q4 uses ~42GB VRAM. Needs 64GB+ RAM. |
| **Performance** | Moderate (8-15 tokens/sec) | Slower, but significantly "smarter". |
| **Use Cases** | • **Deep Reasoning:** Multi-step problem solving.<br>• **Nuance:** Creative writing, marketing strategy generation.<br>• **Large Context:** Analyzing massive reports (30k+ tokens). |

---

## Technical Reference: Memory Usage Rule of Thumb

When provisioning, ensure **Model Size (GB)** < **75% of Total System RAM** to prevent swapping (slowness).

*   **7B Model (Q4):** ~5 GB
*   **8B Model (Q4):** ~6 GB
*   **14B Model (Q4):** ~10 GB
*   **32B Model (Q4):** ~20 GB
*   **70B Model (Q4):** ~42 GB

*Note: Q4 (4-bit quantization) is the industry standard for local deployment, offering negligible quality loss vs. 16-bit float for 50% memory savings.*
