FROM jenkins/jenkins:lts

USER root

# Install necessary packages, Docker CLI, Terraform, Kubectl, Trivy, AWS CLI, and Ansible
RUN apt-get update && \
    apt-get install -y \
        curl \
        wget \
        unzip \
        gnupg2 \
        apt-transport-https \
        lsb-release \
        ca-certificates \
        software-properties-common \
        python3 \
        python3-venv \
        python3-pip && \
    # Install Docker CLI
    curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - && \
    echo "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    # Install Terraform
    wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor > /usr/share/keyrings/hashicorp-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list && \
    apt-get update && \
    apt-get install -y terraform && \
    # Install Kubectl
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/ && \
    # Install Trivy
    wget https://github.com/aquasecurity/trivy/releases/download/v0.56.0/trivy_0.56.0_Linux-64bit.deb && \
    dpkg -i trivy_0.56.0_Linux-64bit.deb && \
    rm trivy_0.56.0_Linux-64bit.deb && \
    # Install AWS CLI
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws/ && \
    # Create a virtual environment for Python and Ansible
    python3 -m venv /opt/ansible_venv && \
    /opt/ansible_venv/bin/pip install --upgrade pip && \
    /opt/ansible_venv/bin/pip install ansible && \
    # Create symlinks to make Ansible easily accessible
    ln -s /opt/ansible_venv/bin/ansible /usr/local/bin/ansible && \
    ln -s /opt/ansible_venv/bin/ansible-playbook /usr/local/bin/ansible-playbook && \
    # Clean up
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER jenkins