# Mac Mini LLM Appliance Business

Pre-provisioned Mac Mini M4 units with local LLM deployment for enterprise customers requiring data sovereignty.

## Business Overview

Sell ready-to-use Mac Mini M4 units pre-configured with:
- Ollama inference server
- Open WebUI interface
- Pre-loaded, optimized models
- Security hardening
- Documentation & support

## Target Customers

- Law firms (client confidentiality)
- Healthcare (HIPAA compliance)
- Financial services (regulatory requirements)
- Government agencies (data sovereignty)
- Research institutions (IP protection)
- SMBs wanting AI without cloud dependency

## Repository Structure

```
├── catalog.md              # Product tiers & model recommendations
├── provisioning/
│   ├── setup.sh            # Main provisioning script
│   ├── models.sh           # Model download & optimization
│   └── security.sh         # Security hardening
├── evaluation/
│   ├── benchmark.sh        # Performance benchmarking
│   └── accuracy-test.py    # Model accuracy evaluation
├── docs/
│   ├── customer-guide.md   # End-user documentation
│   └── maintenance.md      # Maintenance procedures
└── configs/
    └── launchd/            # Auto-start service configs
```

## Quick Start (For Provisioning)

```bash
cd provisioning
chmod +x *.sh
./setup.sh
```

## License

Proprietary - For internal business use
