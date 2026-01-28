# Mac Mini AI Appliance: Provisioning Guide

This guide outlines the process of converting a fresh Mac Mini into a turnkey "AI Appliance" for corporate clients.

## 1. Concept & Value Proposition
You are selling **Privacy & Simplicity**.
Clients buy this box, plug it into their intranet, and immediately have a secure, ChatGPT-like interface that never sends data to the cloud.

## 2. Directory Structure
This folder contains the complete toolset:
- `CATALOG.md`: Sales cheat sheet matching hardware to business needs.
- `scripts/`: Automation for setup and model downloading.
- `docker-compose.yml`: Configuration for the user interface (OpenWebUI).
- `benchmark/`: Tools to verify performance before delivery.

## 3. Hands-on Provisioning Steps

### Phase A: Initial Setup (The "Factory" Stage)
*Perform these steps on the Mac Mini you are preparing for sale.*

1.  **OS Prep**: Create a dedicated admin account (e.g., `ai-admin`).
2.  **Copy Files**: Clone this repository or copy the `mac-llm-appliance` folder to the machine.
3.  **Run Environment Setup**:
    ```bash
    chmod +x scripts/*.sh
    ./scripts/setup_env.sh
    ```
    *This installs Homebrew, Ollama, and Docker.*

### Phase B: Model Loading (Customization)
*Consult `CATALOG.md` to decide which Tier to install.*

1.  **Start Ollama Backend**:
    Open a terminal and run:
    ```bash
    ollama serve
    ```
    *(Keep this window open)*

2.  **Provision Models**:
    In a new terminal window:
    ```bash
    ./scripts/provision_models.sh tier2
    ```
    *(Replace `tier2` with `tier1` or `tier3` as needed)*

### Phase C: UI Deployment
We use OpenWebUI for the user interface.

1.  **Start the Interface**:
    ```bash
    docker-compose up -d
    ```
2.  **Verify**: Open Safari and go to `http://localhost:3000`.
3.  **Create Admin Account**: The first account created becomes the Super Admin. Create this for the client or create a generic one and provide credentials.

### Phase D: Validation (Quality Assurance)
Before shipping, ensure the machine performs adequately.

1.  **Run Benchmark**:
    ```bash
    python3 benchmark/simple_eval.py llama3.1:8b
    ```
2.  **Check Criteria**:
    - **Tier 1/2**: Should see > 25 tokens/sec.
    - **Tier 3**: Should see > 8 tokens/sec.

## 4. Operational Handover (For the Client)
When you deliver the Mac Mini, provide a simple instruction sheet:

1.  **Power On**.
2.  **Connect to Network**.
3.  **Launch Dashboard**: We can script a desktop shortcut that runs `docker-compose up -d` (if not set to auto-start) and opens `http://localhost:3000`.

## 5. Advanced: Model Tuning & Quantization
"Tuning" in this context usually refers to selecting the right **quantization level** (GGUF format).
- We use standard quantization (Q4_K_M) in the scripts as it's the "sweet spot".
- To use custom quantized models (e.g., from HuggingFace), download the `.gguf` file and use a `Modelfile`:
    ```dockerfile
    FROM ./my-custom-model.gguf
    SYSTEM "You are a helpful corporate assistant."
    ```
    Then run: `ollama create my-custom-model -f Modelfile`

## 6. Maintenance
- **Updating Models**: Run `ollama pull [model]` again to fetch the latest layers.
- **Updating UI**: Run `docker-compose pull` and `docker-compose up -d`.
