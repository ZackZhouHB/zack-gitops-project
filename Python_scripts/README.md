# Python Scripts for AWS, Docker, and Microservices

This directory contains a collection of practical Python scripts and projects focused on AWS automation, cloud management, and learning microservice architectures. The projects range from simple standalone scripts to a complete, observable microservices stack deployed on Kubernetes.

## Projects and Scripts Overview

### 1. Python Practice: Building Microservices Step-by-Step

This series of projects (`Python-practice/`) demonstrates the evolution of a simple application into a full-fledged microservices architecture.

*   **01-single-app:** A basic "Hello World" Flask application containerized with Docker.
*   **02-microservice-docker-compose:** The application is split into two services (`user-service` and `order-service`) and orchestrated with Docker Compose.
*   **03-with-api-gateway:** An API Gateway is introduced to act as a single entry point for the microservices.
*   **04-with-consul:** Adds **Consul** for service discovery, allowing services to find each other dynamically.
*   **05-with-ELK:** Integrates the **ELK Stack** (Elasticsearch, Logstash, Kibana) for centralized logging, with services sending logs via GELF.
*   **06-with-monitoringstack:** Adds **Prometheus** and **Grafana** to the stack for metrics collection and visualization.
*   **07-with-k8s:** Shows how to deploy the microservices to a Kubernetes cluster.

#### How to Run the Microservices Projects

Each of the Docker-based projects can be run using Docker Compose.

1.  **Navigate to the project directory:**
    ```bash
    cd Python-practice/06-with-monitoringstack # (Example)
    ```
2.  **Build and run the containers:**
    ```bash
    docker-compose up --build
    ```

---

### 2. AWS EC2 Agent Checker

Located in the `agent-checker/` directory, this is a powerful, modular script for scanning EC2 instances across multiple AWS accounts to verify the installation status and version of various agents (e.g., Airlock, Dynatrace).

*   **`modu.py`**: The main script, designed with a plugin-style architecture using Python's abstract base classes. New agents can be added easily by creating a new checker class.
*   **Features:**
    *   Automatically discovers and iterates through all configured AWS profiles.
    *   Handles both Linux (dpkg, rpm) and Windows (PowerShell) environments.
    *   Provides comprehensive CSV reporting.

#### How to Use

```bash
# Check for the Airlock agent in the 'nonprod' profile
python3 agent-checker/modu.py --profiles nonprod --agent airlock --output airlock_status.csv

# Check for the Dynatrace agent in all configured profiles
python3 agent-checker/modu.py --agent dynatrace --output dynatrace_status.csv
```

---

### 3. AWS Resource Management Scripts

This collection includes scripts for managing EC2 tags, IAM users, and terminating instances, with support for both single and multiple AWS accounts.

*   **EC2 Tag Management (`single-aws-account/`, `mutiple-aws-accounts/`)**
    *   **`export1.py` / `export2.py`**: Export a list of all EC2 instances and their tags to a CSV file.
    *   **`update1.py` / `update_tags_2.py`**: Read an updated CSV file and apply the specified tags to the corresponding EC2 instances.

*   **IAM User Creation (`user_creation/`)**
    *   **`iam-single.py`**: Creates a single IAM user with a predefined password and policy across multiple AWS accounts.
    *   **`more_user_from_csv.py`**: Reads a list of usernames from a CSV file and creates them in all specified AWS accounts.

*   **EC2 Instance Termination (`deleteEC2/`)**
    *   **`deleteec2.py`**: Safely terminates a list of EC2 instances from a CSV file. It automatically handles the detachment and deletion of associated EBS volumes and the release of Elastic IPs.

*   **Other AWS Scripts**
    *   **`app-sg-allow-22.py`**: A sample Lambda function to detect and send an email alert when a security group is configured to allow inbound traffic on port 22 from the internet (0.0.0.0/0).
    *   **`app-untagged.py`**: A script to identify and list all EC2 instances that are missing a mandatory `Owner` tag.

### General Setup

*   **Python & Dependencies:** Ensure you have Python 3 installed. Most scripts use the `boto3` library, which can be installed via pip:
    ```bash
    pip install boto3
    ```
*   **AWS Credentials:** The scripts that interact with AWS require your credentials to be configured. The recommended way is to set up profiles in your `~/.aws/config` and `~/.aws/credentials` files.
