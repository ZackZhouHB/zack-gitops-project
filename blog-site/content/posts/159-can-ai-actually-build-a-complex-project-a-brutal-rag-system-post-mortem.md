---
title: "Can AI Actually Build a Complex Project? A Brutal RAG System Post-Mortem"
date: 2026-03-01T05:27:11Z
slug: can-ai-actually-build-a-complex-project-a-brutal-rag-system-post-mortem
categories: ["Machine Learning"]
aliases: ["/post/159/"]
legacy_id: 159
---
Last month, I did something that, looking back, was probably the most educational practice of my year. I tried using Claude and GPT to build a complete multi-source RAG system from scratch. This wasn't a "toy demo" for social media; it was a real internal tool for my lab designed to handle messy document data, query rewriting, hybrid search, and deployment for my team.

I set a strict rule for myself: **Let the AI write almost all the code, while I handle the requirements and decision-making.**

**The Illusion of Productivity**

For the first three hours, I felt like the world had changed. AI drafted the architecture—clean and beautiful. It wrote the backend code using FastAPI and LangChain, built the React frontend components one by one, and even configured the Dockerfile and Nginx reverse proxy settings perfectly.

It felt like having a partner who knows everything and never gets tired. I genuinely believed that at this efficiency, solo developers were about to take off. Then, the integration phase began, and **I hit a brick wall for a solid week.**

**The Chasm Between "Complete" and "Production-Ready"**

AI is unparalleled at getting you from "0 to 0.6." It nukes the boilerplate work. However, between a "seemingly complete" project and one that actually runs in production lies a chasm deeper than you imagine. That chasm contains:

- **Edge cases** and hidden coupling between modules.
- **Tacit knowledge** (e.g., business constraints that aren't in the database schema but exist in human heads).
- **Race conditions** and a hundred ways users can break the system that AI cannot foresee.

This final 20% of the project often takes **three to five times longer** than the initial 80%.

**The Hardest Parts Aren't About Writing Code**

Complexity in software doesn't come from the volume of code, but from three specific areas:

- **State Space Explosion:** Systems have dozens of components with internal states. AI lacks the "gut feeling" of a seasoned engineer who knows which combinations are likely to fail.
- **The Domino Effect of Decisions:** Every technical choice (like choosing Redis over Memcached) impacts future consistency and scaling. AI can list pros and cons, but it cannot make a comprehensive trade-off based on team capability or future business direction.
- **Fuzzy Requirements:** Real projects are rarely well-defined. Navigating ambiguity and converging on real needs is a human capability that AI lacks.

**A Week of Hitting the Wall: My Diary**

```text
Day 1: Smooth sailing. AI built the skeleton and basic API routes.
Day 2: The pipeline failed. AI's PDF code worked on clean papers but failed on lab scans and handwritten notes. Swapping libraries broke downstream modules.
Day 3-4: AI implemented hybrid search but forgot to normalize scores. The BM25 scores drowned out the vector similarities. AI doesn't think about how code behaves on real data distributions.
Day 5-6: Deployment hell. CUDA version mismatches, OOM errors, and Nginx conflicts with SSE streaming. Every fix AI suggested was for an outdated library version.
Day 7: Finally got it running, but I was exhausted.
```

**The Core Realization: Your Own Capability**

AI's helpfulness is directly proportional to the skill of the user. It is an engine, and you are the driver.

- **If you are an expert:** AI is a 3-5x multiplier. You spot bugs instantly and know exactly how to guide the engine.
- **If you are a beginner:** AI takes you to the "looks okay" stage, and then you get stuck. You enter a "death loop" of asking AI for fixes that create new, incomprehensible bugs.

**What AI Still Cannot Do**

- **Cross-file logic consistency:** AI lacks a persistent "mental model" of a project with dozens of files.
- **Performance profiling:** AI writes functional code, but it doesn't naturally account for N+1 queries or memory deep copies.
- **System-level debugging:** When bugs involve the OS, kernel parameters, or third-party service interactions, AI is often useless.
- **The Human Element:** Negotiating requirements and understanding unstated concerns is 30% of a project's success.

**The New Definition of "Doing a Project"**

In the AI era, coding is being compressed. The new core skills are **understanding the problem**, **evaluating AI-generated solutions**, and **integration**. AI has removed the "manual labor" of programming, leaving behind only the "intellectual labor."

AI can help you finish a complex project, but it cannot do it well without you. It is your engine, but you must know where you are going. The stronger the AI becomes, the more you actually need to understand the underlying systems to stay in control.
