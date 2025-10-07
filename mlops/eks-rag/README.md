# AWS EKS RAG with Weaviate

## Introduction

This project creates a production-ready Retrieval-Augmented Generation (RAG) system on Amazon EKS. It hosts a custom RAG pipeline for querying internal documents and a general-purpose chatbot using OpenWebUI. The goal is to provide a scalable, cost-effective AI platform for internal team use.

## System Architecture

The architecture is a microservices-based system running on Kubernetes.

*   **Infrastructure (Terraform & EKS):** The entire infrastructure, including the VPC, EKS cluster, and AWS services (S3, EFS), is defined using Terraform for automated and repeatable deployments.
*   **Backend (FastAPI):** A Python-based FastAPI application serves as the core API. It handles document uploads to S3, manages the RAG query lifecycle, and integrates with Amazon Bedrock for language model generation.
*   **Vector Database (Weaviate):** Weaviate is used as the vector database, deployed as a StatefulSet within the EKS cluster. It was chosen over managed services like Kendra for lower latency and cost. It stores document embeddings and performs fast similarity searches.
*   **Frontend (React & Nginx):** A simple React single-page application provides the user interface for uploading documents and asking questions. It is served by an Nginx container that also acts as a reverse proxy to the backend API.

## Core Workflows

*   **Document Ingestion:** Users upload documents (PDF, DOCX, etc.) through the web interface. The backend stores the file in S3, extracts the text, generates vector embeddings, and indexes them in Weaviate.
*   **Query Processing:** When a user asks a question, the backend creates a vector embedding of the query, searches Weaviate for the most relevant document chunks, and then passes this context along with the original question to Amazon Bedrock (Claude 3.5 Haiku) to generate a grounded answer.

## Conclusion

This project successfully demonstrates how to build a scalable, cloud-native RAG system using open-source tools like Weaviate alongside managed AWS services. It provides a powerful and cost-effective solution for internal knowledge management.

## Source Code

The full application, Terraform code, and EKS manifests are available at the [GitHub repository](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/mlops/eks-rag).
