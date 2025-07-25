# GitOps and Kubernetes Projects

This repository contains a collection of projects demonstrating various GitOps principles and advanced Kubernetes concepts. Each directory showcases a different aspect of building, managing, and deploying applications on Kubernetes, from infrastructure provisioning to application lifecycle management.

## Projects Overview

1.  **[EKS with Karpenter and Spot Instances](./EKS-Karpenter-Spot/)**: A Terraform project to provision a cost-optimized and auto-scaling AWS EKS cluster using Karpenter for dynamic node provisioning with Spot Instances.
2.  **[Kubernetes on EC2 with Ansible](./k8s-on-ec2-with-ansible/)**: A project that builds a Kubernetes cluster from the ground up on AWS EC2 instances using Terraform for infrastructure and Ansible for configuration and bootstrapping.
3.  **[Argo CD Application Deployments](./argo-helm-zackblog/)**: Examples of deploying applications to Kubernetes using the GitOps pattern with Argo CD. This includes a Helm-based deployment and a standard manifest deployment.
4.  **[PostgreSQL Operator on Kubernetes](./postgrsql-operator/)**: Demonstrates how to deploy and manage stateful applications (PostgreSQL databases) on Kubernetes using the CrunchyData PostgreSQL Operator.
5.  **[Retail Microservices Application](./retail-mircoservice-app/)**: A sample polyglot microservices application deployed on Kubernetes, showcasing a real-world application architecture.

---

## 1. EKS with Karpenter and Spot Instances

This project uses Terraform to provision a modern, cost-effective, and auto-scaling AWS EKS cluster. It leverages **Karpenter** to dynamically launch and terminate EC2 Spot Instances based on workload demands, significantly reducing compute costs.

### Key Technologies
*   **Terraform**
*   **AWS EKS**
*   **Karpenter**
*   **AWS Spot Instances**

### How to Use

1.  **Navigate to the directory:**
    ```bash
    cd EKS-Karpenter-Spot
    ```

2.  **Initialize and apply Terraform:**
    ```bash
    terraform init
    terraform apply
    ```

3.  **Configure `kubectl`:**
    After the apply is complete, Terraform will output a command to configure `kubectl` for your new cluster. Run that command.

4.  **Deploy a Sample Workload:**
    Deploy the sample application to test Karpenter's node provisioning:
    ```bash
    kubectl apply -f workload.yaml
    ```
    Karpenter will automatically provision new Spot instances to accommodate the pods.

---

## 2. Kubernetes on EC2 with Ansible

This project provides a more hands-on approach to building a Kubernetes cluster. It uses Terraform to provision the underlying EC2 instances and Ansible to configure the nodes and bootstrap a cluster using `kubeadm`.

### Key Technologies
*   **Terraform**
*   **Ansible**
*   **AWS EC2**
*   **Kubeadm**

### How to Use

1.  **Navigate to the directory:**
    ```bash
    cd k8s-on-ec2-with-ansible
    ```

2.  **Provision Infrastructure:**
    Use Terraform to create the EC2 instances for the master and worker nodes.
    ```bash
    terraform init
    terraform apply
    ```

3.  **Configure and Run Ansible:**
    The Ansible playbooks are designed to be run in sequence to set up the cluster. Update the inventory file (`aws_ec2.yaml`) with your instance details and run the playbooks.
    ```bash
    # Example of running a playbook
    ansible-playbook 3-k8s-nodes-preparation.yaml
    ansible-playbook 4-master-init.yaml
    # ... and so on
    ```

---

## 3. Argo CD Application Deployments

These projects demonstrate the GitOps workflow using Argo CD to deploy applications to Kubernetes. The repository contains manifests for two sample applications:

*   **`argo-helm-zackblog`**: A Jekyll-based blog deployed using a Helm chart.
*   **`argocd-joesite`**: A simple web application deployed with standard Kubernetes manifests.

### Key Technologies
*   **Kubernetes**
*   **Argo CD**
*   **Helm** (for `zackblog`)

### How to Use

1.  **Prerequisites:** A running Kubernetes cluster with Argo CD installed.

2.  **Deploy an Application:**
    Apply the `application.yaml` manifest from the desired project directory to your cluster. Argo CD will detect the application and automatically sync the resources defined in this Git repository.

    ```bash
    # Deploy the Helm-based blog
    kubectl apply -f argo-helm-zackblog/application.yaml

    # Deploy the simple web app
    kubectl apply -f argocd-joesite/application.yaml
    ```
    You can then view and manage the application from the Argo CD UI.

---

## 4. PostgreSQL Operator on Kubernetes

This project demonstrates how to manage stateful applications like PostgreSQL on Kubernetes using the **CrunchyData PostgreSQL Operator**. The operator automates the creation, management, and scaling of PostgreSQL clusters.

### Key Technologies
*   **Kubernetes**
*   **PostgreSQL Operator (CrunchyData)**
*   **Kustomize**

### How to Use

1.  **Install the Operator:**
    Use Kustomize to apply the operator manifests to your cluster.
    ```bash
    kubectl apply -k postgrsql-operator/install/default
    ```

2.  **Deploy a PostgreSQL Cluster:**
    Once the operator is running, you can create a new PostgreSQL database by applying the `PostgresCluster` custom resource.
    ```bash
    kubectl apply -k postgrsql-operator/postgres
    ```
    The operator will handle the provisioning of the StatefulSet, Services, and Secrets required for the database.

3.  **Deploy Keycloak with a PostgreSQL Backend:**
    The `keycloak` directory contains an example of deploying Keycloak using the PostgreSQL database managed by the operator.
    ```bash
    kubectl apply -k postgrsql-operator/keycloak
    ```

---

## 5. Retail Microservices Application

This project contains the Kubernetes manifests for a sample polyglot microservices application. It is designed to be deployed with Argo CD and showcases a more complex, real-world application architecture.

### Key Technologies
*   **Kubernetes**
*   **Argo CD**
*   **Microservices Architecture**

### How to Use

1.  **Prerequisites:** A running Kubernetes cluster with Argo CD installed.

2.  **Deploy the Application:**
    Apply the `application.yaml` manifest to your cluster.
    ```bash
    kubectl apply -f retail-mircoservice-app/application.yaml
    ```
    Argo CD will deploy all the microservices, databases (MySQL, PostgreSQL, Redis, DynamoDB), and messaging components (RabbitMQ) defined in the `deploy.yaml` file.
