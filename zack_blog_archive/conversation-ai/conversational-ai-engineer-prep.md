# Conversational AI Engineer — Skills Gap Analysis & Hands-On Preparation Plan

## 1. Background

### 1.1 Target Role

**AI Engineer – Conversational** at 4WD Supacentre (Sydney, NSW)

The role focuses on designing, building, and deploying AI-powered **chat** (ecommerce website) and **voice** (contact centre) solutions. The company operates on **Salesforce** for both voice calls and website chat, and is open to best-of-breed conversational AI tooling.

### 1.2 What the Company Is Trying to Achieve

- **AI Chat on Website:** Customers shopping on the 4WD Supacentre ecommerce site interact with an intelligent chatbot that can answer product questions, check order status, handle returns/exchanges, and escalate to a human agent when needed.
- **AI Voice in Contact Centre:** Customers calling the support line are greeted by an AI voice agent that understands their request, resolves common queries automatically, and routes complex issues to the right human agent — reducing wait times and handling costs.
- **CRM Integration:** All conversations (chat and voice) are logged in Salesforce, creating cases, updating customer records, and providing agents with full context when a handoff occurs.
- **Continuous Improvement:** The AI systems are monitored via KPIs (containment rate, CSAT, deflection, resolution) and iteratively improved.

### 1.3 Your Current Skills

| Skill Area | Your Experience |
|---|---|
| LLM & GenAI | AWS Bedrock (model invocation via model ID), RAG pipelines |
| Infrastructure | Docker, EKS, containerised deployments |
| Frontend | Open WebUI, custom chat frontends |
| Backend | Weaviate vector DB, API integrations |
| Cloud | AWS (compute, networking, EKS, Bedrock) |
| AI Application Pattern | RAG-based Q&A, open-ended LLM chat |

### 1.4 Skills Gap Summary

| Required by JD | Your Current Level | Gap |
|---|---|---|
| Intent-based NLU (classification, entities, slots) | Not practiced | 🔴 High |
| Multi-turn dialogue management & conversation design | Not practiced | 🔴 High |
| Conversational AI platforms (Lex, Einstein Bots, etc.) | Not practiced | 🔴 High |
| AI Voice / telephony (TTS, STT, phone integration) | Not practiced | 🔴 High |
| Salesforce CRM integration | Not practiced | 🔴 High |
| Contact centre platforms (Amazon Connect, Genesys) | Not practiced | 🟡 Medium |
| Conversational KPIs & analytics | Conceptual only | 🟡 Medium |
| Cloud infrastructure (AWS) | Strong | 🟢 Low |
| API / webhook integrations | Strong | 🟢 Low |
| LLM / GenAI applied to conversations | Partial (RAG) | 🟢 Low |
| Docker / containerised deployment | Strong | 🟢 Low |

---

## 2. Proposed Approach

### 2.1 Philosophy

Build a **realistic end-to-end conversational AI system** that mirrors what the JD describes — not just isolated tutorials, but a working prototype that you can demo and talk through in an interview. The system will cover:

1. **Website AI Chatbot** — intent-based + RAG-enhanced
2. **AI Voice Agent** — phone-callable, integrated with the same backend
3. **CRM Integration** — Salesforce as the system of record
4. **Analytics** — basic KPI tracking and conversation logging

### 2.2 Technology Stack (Personal Lab)

```
┌─────────────────────────────────────────────────────────┐
│                     USER CHANNELS                       │
│  📱 Phone (your mobile)     💻 Web Chat (React/HTML)    │
└──────────┬──────────────────────────┬───────────────────┘
           │                          │
┌──────────▼──────────┐   ┌──────────▼───────────────────┐
│   Amazon Connect    │   │   Web Chat Frontend          │
│   (Contact Centre)  │   │   (React or HTML/JS)         │
│   - Phone number    │   │   - Lex Web UI SDK           │
│   - IVR flows       │   │   - Hosted in Docker/S3      │
└──────────┬──────────┘   └──────────┬───────────────────┘
           │                          │
           └──────────┬───────────────┘
                      │
           ┌──────────▼──────────┐
           │    Amazon Lex V2    │
           │  (NLU/NLP Engine)   │
           │  - Intents          │
           │  - Slots/Entities   │
           │  - Multi-turn flows │
           └──────────┬──────────┘
                      │
           ┌──────────▼──────────┐
           │   AWS Lambda        │
           │  (Fulfillment)      │
           │  - Business logic   │
           │  - API orchestrator │
           └──────┬─────┬────────┘
                  │     │
       ┌──────────▼┐  ┌▼──────────────┐
       │ Salesforce │  │ AWS Bedrock   │
       │ Dev Org    │  │ (RAG/GenAI)   │
       │ - Cases    │  │ - Knowledge   │
       │ - Contacts │  │ - Weaviate DB │
       │ - Orders   │  │ - Fallback QA │
       └────────────┘  └───────────────┘
```

### 2.3 Cost Estimate

| Service | Free Tier / Cost |
|---|---|
| Amazon Lex V2 | 10,000 text / 5,000 speech requests free (first year) |
| Amazon Connect | Pay-per-use ~$0.018/min for voice |
| Amazon Polly (TTS) | 5 million chars/month free (first year) |
| AWS Lambda | 1M requests/month free |
| AWS Bedrock | Pay-per-token (minimal for lab use) |
| Salesforce Developer Org | Free forever |
| Weaviate | Docker (local, free) |
| Botpress / Rasa (optional) | Open source, Docker (local, free) |

**Estimated monthly cost: $5–15 USD** for moderate experimentation.

---

## 3. Hands-On Lab Plan

### Phase 1: Conversational AI Fundamentals (Week 1–2)

**Goal:** Understand intent-based NLU — the core paradigm shift from RAG-only thinking.

#### Lab 1.1 — Amazon Lex V2: Your First Intent-Based Bot

**What to build:** A retail customer service bot with structured intents.

**Intents to design:**

| Intent | Sample Utterances | Slots/Entities |
|---|---|---|
| `CheckOrderStatus` | "Where is my order", "Track my delivery" | `OrderNumber`, `Email` |
| `ReturnItem` | "I want to return something", "How do I get a refund" | `OrderNumber`, `ProductName`, `Reason` |
| `ProductInquiry` | "Do you have roof racks for Hilux", "Is this in stock" | `ProductCategory`, `VehicleMake` |
| `StoreHours` | "What time do you open", "Are you open Sunday" | `StoreLocation` |
| `SpeakToHuman` | "I want to talk to a person", "Transfer me" | — |
| `FallbackIntent` | (anything unmatched) | — |

**Steps:**
1. Create a Lex V2 bot in AWS Console
2. Define each intent with 15–20 sample utterances per intent
3. Configure slots with prompts ("What's your order number?")
4. Design confirmation prompts and fulfilment responses
5. Test in the Lex console — iterate on utterance coverage
6. Add `FallbackIntent` with escalation message

**Key learning:** How intent classification differs from RAG retrieval. In Lex, the bot identifies *what the user wants to do* (intent) and *extracts structured data* (slots), rather than searching documents.

#### Lab 1.2 — Multi-Turn Dialogue Design

**What to build:** A multi-step return flow that collects information across turns.

**Conversation flow:**
```
User: I want to return an item
Bot:  I can help with that. What's your order number?
User: ORD-12345
Bot:  Got it. Which item would you like to return?
User: The roof rack
Bot:  What's the reason for the return?
User: It doesn't fit my car
Bot:  I'll create a return for the roof rack from order ORD-12345.
      Reason: Doesn't fit. Shall I proceed?
User: Yes
Bot:  Done! Return case RET-001 created. You'll receive an email
      with return instructions.
```

**Steps:**
1. Configure slot elicitation order in Lex
2. Add conditional branching (e.g., if item is outside return window → different response)
3. Add confirmation step before fulfillment
4. Handle "cancel" mid-flow gracefully
5. Handle slot corrections ("Actually, it's ORD-12346")

---

### Phase 2: Voice AI & Telephony (Week 3–4)

**Goal:** Build a phone-callable AI voice agent — the other half of the JD.

#### Lab 2.1 — Amazon Connect + Lex Voice Bot

**What to build:** A working phone number that answers with your AI bot.

**Steps:**
1. Set up Amazon Connect instance (free tier)
2. Claim a phone number (DID)
3. Create a contact flow:
   - Welcome prompt: "Thanks for calling 4WD Supacentre. How can I help?"
   - Wire to your Lex bot from Phase 1
   - Add "Get customer input" block → Lex bot
   - Handle escalation: transfer to queue / play message
4. Call your number from your mobile — test the full voice experience
5. Tune for voice:
   - Adjust utterances for spoken language ("Yeah" vs "Yes")
   - Configure SSML in Polly for natural speech
   - Handle silence/no-input timeouts
   - Handle barge-in (user interrupts bot)

**Key learning:** Voice adds latency (STT → NLU → Logic → TTS). You'll feel the same delay you noticed calling car sales bots. Optimising this is a real skill.

#### Lab 2.2 — Voice-Specific Challenges

**Exercises:**
1. **Barge-in handling:** Configure bot to stop speaking when user interrupts
2. **DTMF fallback:** Allow "Press 1 for orders, 2 for returns" as backup
3. **Disambiguation:** When STT misrecognises, handle gracefully ("Did you say order 1-2-3-4-5?")
4. **Sentiment detection:** Use Connect's real-time sentiment → route angry callers to humans faster
5. **Call recording:** Enable and review transcripts to improve utterances

---

### Phase 3: CRM Integration — Salesforce (Week 5–6)

**Goal:** Connect your bot to Salesforce so conversations create real CRM records.

#### Lab 3.1 — Salesforce Developer Org Setup

**Steps:**
1. Sign up at [developer.salesforce.com](https://developer.salesforce.com) (free)
2. Set up basic objects:
   - **Contacts** — customer records
   - **Cases** — support tickets (return requests, complaints)
   - **Custom Object: Orders** — mock order data
3. Populate with sample data (20–30 fake orders, 10 contacts)
4. Create a Connected App for API access (OAuth 2.0 client credentials flow)

#### Lab 3.2 — Lambda → Salesforce Integration

**What to build:** When your Lex bot fulfils an intent, Lambda creates/updates Salesforce records.

**Integration flows:**

| Bot Intent | Salesforce Action |
|---|---|
| `CheckOrderStatus` | Query Order object → return status to user |
| `ReturnItem` | Create Case (type: Return) with order details |
| `SpeakToHuman` | Create Case (type: Escalation) + log transcript |
| `ProductInquiry` | Log interaction on Contact record |

**Steps:**
1. Write Lambda function (Python/Node) to authenticate with Salesforce API
2. Implement SOQL queries for order lookup
3. Implement Case creation with conversation context
4. Wire Lambda as Lex fulfilment hook
5. Test end-to-end: say "I want to return my order" → check Salesforce for new Case

#### Lab 3.3 — Salesforce Einstein Bots (Bonus)

**Steps:**
1. In your Developer Org, enable Einstein Bots
2. Build a simple bot natively in Salesforce
3. Compare the experience with Lex (capabilities, limitations, ease of use)
4. Understand when you'd recommend Einstein Bots vs external NLU

---

### Phase 4: RAG Enhancement — Your Strength (Week 7–8)

**Goal:** Layer your existing Bedrock/RAG skills onto the intent-based system.

#### Lab 4.1 — Knowledge-Augmented Responses

**What to build:** When the bot can't answer a product question via intents, fall back to RAG.

**Architecture:**
```
User: "What's the weight capacity of the Adventure Kings rooftop tent?"
  → Lex: Intent = ProductInquiry, but no structured answer
  → Lambda: Query Bedrock RAG (product catalog in Weaviate)
  → Return grounded answer with source
```

**Steps:**
1. Load mock product catalog into Weaviate (reuse your existing RAG skills)
2. In Lambda, detect when Lex can't fully resolve → call Bedrock
3. Return RAG answer through Lex response
4. Add guardrails: don't hallucinate prices or stock levels

#### Lab 4.2 — Generative Conversation Summaries

**What to build:** After each conversation, generate a summary and attach to the Salesforce Case.

**Steps:**
1. Collect conversation turns in Lambda (or Connect contact trace)
2. Call Bedrock to summarise: "Customer called about returning a roof rack from order ORD-12345. Reason: doesn't fit vehicle. Return case created."
3. Attach summary to Salesforce Case notes
4. This is a genuine value-add that combines your GenAI skills with CRM integration

---

### Phase 5: Analytics & KPIs (Week 9–10)

**Goal:** Build the monitoring layer — this is what separates a prototype from a production system.

#### Lab 5.1 — Conversation Logging & Metrics

**KPIs to track:**

| Metric | Definition | How to Measure |
|---|---|---|
| **Containment Rate** | % of conversations resolved without human handoff | Count `SpeakToHuman` intents / total conversations |
| **Intent Match Rate** | % of utterances correctly classified | Count fallback triggers / total utterances |
| **CSAT** | Customer satisfaction | Post-conversation survey (Connect has this built-in) |
| **Avg Handle Time** | Time from start to resolution | Timestamp diff in conversation logs |
| **Deflection Rate** | % of queries handled by bot vs total incoming | Bot-handled / (bot + human agent) |

**Steps:**
1. Log every conversation turn to DynamoDB or CloudWatch
2. Build a simple dashboard (CloudWatch dashboard or QuickSight)
3. Identify underperforming intents (high fallback rate)
4. Iterate: add more training utterances, adjust flows
5. Document before/after metrics

#### Lab 5.2 — A/B Testing Conversation Flows

**Exercise:**
1. Create two versions of the greeting ("How can I help?" vs offering menu options)
2. Route 50% of traffic to each
3. Measure which has better containment rate
4. Document findings — this is interview gold

---

### Phase 6: Open Source Alternative (Optional, Week 11–12)

**Goal:** Get hands-on with a platform-agnostic conversational AI framework.

#### Lab 6.1 — Rasa or Botpress (Docker-Based)

**Why:** Shows you understand conversational AI beyond just AWS tooling.

**Steps:**
1. Run Rasa Open Source in Docker (you already know Docker well)
2. Replicate your Lex bot's intents and flows in Rasa
3. Train the NLU pipeline locally — understand tokenisation, featurisation, intent classification under the hood
4. Build custom actions (equivalent to Lambda fulfillment)
5. Compare: Lex (managed) vs Rasa (self-hosted) — trade-offs

This is valuable because in interviews, you can discuss platform evaluation — exactly what the JD asks for ("Evaluate and recommend conversational AI platforms").

---

## 4. Project Portfolio Deliverables

By the end, you should have:

| # | Deliverable | Maps to JD Requirement |
|---|---|---|
| 1 | Working Lex chatbot with 5+ intents and multi-turn flows | "Design and implement AI-powered chat solutions" |
| 2 | Phone-callable voice agent via Amazon Connect | "Architect and deploy AI voice solutions" |
| 3 | Salesforce integration (case creation, order lookup) | "Integrate with Salesforce CRM" |
| 4 | RAG-enhanced product knowledge responses | "Build, train and continuously improve NLP models" |
| 5 | Conversation analytics dashboard with KPIs | "Define and monitor key performance metrics" |
| 6 | Technical design document for the full system | "Document technical designs and integration architectures" |
| 7 | Platform comparison (Lex vs Rasa/Botpress vs Einstein) | "Evaluate and recommend conversational AI platforms" |

---

## 5. Estimated Coverage

With this lab plan completed, you would cover approximately:

- **70–75%** of the technical skills in the JD
- **50%** of the platform-specific experience (enterprise tools like Genesys, Cognigy remain inaccessible)
- **90%** of the architectural understanding needed
- **40%** of the production/scale experience (only achievable on the job)

The remaining gaps (enterprise scale, multi-agent contact centres, production SLA management) are things most employers expect you to learn on the job — having the hands-on foundation above makes you a credible candidate who can ramp quickly.

---

## 6. Resources

- [Amazon Lex V2 Developer Guide](https://docs.aws.amazon.com/lexv2/)
- [Amazon Connect Administrator Guide](https://docs.aws.amazon.com/connect/)
- [Salesforce Developer Org Signup](https://developer.salesforce.com/signup)
- [Salesforce REST API Guide](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/)
- [Rasa Open Source Docs](https://rasa.com/docs/rasa/)
- [Botpress Documentation](https://botpress.com/docs)
- [AWS Bedrock Developer Guide](https://docs.aws.amazon.com/bedrock/)
- [Conversational Design by Google](https://designguidelines.withgoogle.com/conversation/)
