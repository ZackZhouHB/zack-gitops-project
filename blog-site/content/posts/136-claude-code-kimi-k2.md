---
title: "Claude Code + Kimi K2"
date: 2025-07-19T00:40:01Z
slug: claude-code-kimi-k2
categories: ["DevOps"]
aliases: ["/post/136/"]
legacy_id: 136
---
**Effortless Coding with Claude Code and Kimi K2: Features, Pricing, and Setup Guide**

Recently Kimi K2 became one of the most popular model in HuggingFace, claimed its compatible with Claude Code API. With my new sign up and got a $15 free credit, Let's see how it can intergrate with Claud Code and validate its coding performance!

---

**🧠 Claude Code + Kimi K2?**

**Claude Code** is command-line tool from Anthropic Claude, powered by its latest models (Opus, Sonnet, Haiku). It is highly effective but can be expensive.

**Kimi K2** is a recently released model from Moonshot AI. It offers similar AI coding capabilities at a much lower price.

**Key Features:**
- Claude-compatible prompt API
- Low latency and stable access in China
- Affordable pricing

---

**📈 Pricing Comparison (Per 1 Million Tokens)**

| Model/API | Input Cost | Output Cost | Total |
| --- | --- | --- | --- |
| Claude Opus | $15 | $75 | $90 |
| Claude Sonnet | $3 | $15 | $18 |
| Claude Haiku | $0.80 | $4 | $4.80 |
| Kimi K2 | ~0.50 | ~$2.50 | ~**$3.05** |

***Kimi K2 is over 90% cheaper** than Claude Opus and significantly less expensive than Sonnet or Haiku, making it ideal for budget-conscious developers (like me).*

---

**✨ Installation Guide (Node.js Setup)**

**Step 1: Environment Preparation**
Ensure you have Node.js 18+ installed:

```bash
# Check versions
root@zack:~# node -v
v20.19.3
root@zack:~# npm -v
11.4.2
```

**Step 2: Install Claude Code CLI**

```bash
# Global install
npm install -g @anthropic-ai/claude-code

# Launch the interface
claude
```

---

**🚀 Kimi K2 API Integration**

**1. Get the Kimi API Key**
Register at the [Moonshot Console](https://moonshot.cn) and generate an API Key.

[![[Image Placeholder 01: Moonshot]](/images/kimi6.png)](/images/kimi6.png)

**2. Configure Environment Variables**
For Bash (Linux/WSL):

```bash
# Add variables to your shell profile
echo 'export ANTHROPIC_BASE_URL="https://api.moonshot.cn/anthropic/"' >> ~/.bashrc
echo 'export ANTHROPIC_API_KEY="your_Kimi_API_Key"' >> ~/.bashrc

# Reload the profile to apply changes
source ~/.bashrc
```

**Final Step: Verify the Launch**
Run the tool again:

```text
claude
```

BINGO! We see the API source listed as `API Base URL: https://api.moonshot.cn/anthropic/` . This confirms that Claude Code is now using the Kimi K2 API via the overridden environment variables.

[![[Image Placeholder 01: Kimiapi]](/images/kimi0.png)](/images/kimi0.png)

---

**Fixing My Blog's CSS Overflow Issue**

For a long time, I had been bothered by a persistent content and code snippet overflow issue on [my blog](https://zackblog.work). Due to my limited frontend expertise, I couldn't fix the CSS, even after trying several other AI tools (like GPT-3o, Gemini 2.5 Pro, and DeepSeek R1). I decided to see if the Claude Code + Kimi K2 combo could solve the problem.

Once I explained the issue, you see it correctly started to analyze project's folder structure, identifying the key CSS files which handle the media and view, and suggesting what needed to be adjusted.

[![[Image Placeholder 01: Kimiapi]](/images/kimi2.png)](/images/kimi2.png)

Then requested it to update the code file on my behalf.

[![[Image Placeholder 01: Kimiapi]](/images/kimi3.png)](/images/kimi3.png)

Seems the initial fix only worked for the vertical orientation but not horizontal, so a little more iteration was needed.

[![[Image Placeholder 01: Kimiapi]](/images/kimi4.png)](/images/kimi4.png)

[![[Image Placeholder 01: Kimiapi]](/images/kimi5.png)](/images/kimi5.png)

---

Well done, the issue was completely resolved! All together toke less than 5 minutes via API with less the $0.77 spending!!

[![[Image Placeholder 01: Kimiapi]](/images/kimi7.png)](/images/kimi7.png)

---

**✨ Conclusion**

The combination of the Claude Code CLI with the Kimi K2 API is a powerful and cost-effective setup for AI-assisted coding. If you're after the absolute best performance and don't mind the cost, Claude Code is your go-to. But for excellent value with similar features, **Kimi K2 is a clear winner**.
