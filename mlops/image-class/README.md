# Pneumonia Detection from Chest X-Ray Images

This project is an end-to-end machine learning application that classifies chest X-ray images to detect pneumonia. It covers the entire MLOps lifecycle, from data acquisition and model training on the cloud to deploying the model as a containerized web application.

## Project Overview

The goal is to build a reliable image classification model and make it accessible through a simple web interface. A user can upload a chest X-ray image, and the application will return a prediction of either "Normal" or "Pneumonia."

### Key Components:

1.  **Data Science & Modeling (Jupyter Notebooks):**
    *   The core machine learning workflow is detailed in the notebooks (`cv-aws.ipynb` and `zack-image-classification.ipynb`).
    *   **Dataset:** We use the "Chest X-Ray Images (Pneumonia)" dataset from Kaggle.
    *   **Preprocessing:** Images are resized to a standard 224x224 resolution and organized into training, testing, and validation sets.
    *   **Model:** A **ResNet18** model, pre-trained on ImageNet, is fine-tuned for this binary classification task using PyTorch.
    *   **Training:** The model is trained and tuned using **AWS SageMaker**, demonstrating a cloud-based MLOps approach.

2.  **Backend API (`model-docker/`):
    *   A lightweight **Flask** application serves the trained PyTorch model.
    *   It exposes a `/predict` endpoint that accepts an image file and returns the classification result.
    *   The entire backend is containerized using **Docker** for portability and easy deployment.

3.  **Frontend (`frontend/`):
    *   A simple and user-friendly web interface built with **HTML, CSS, and JavaScript**.
    *   It allows users to upload an X-ray image directly from their device and displays the model's prediction.

4.  **Deployment (`docker-compose.yml`):
    *   The frontend and backend services are orchestrated using **Docker Compose**.
    *   This allows the entire application to be launched with a single command, ensuring that the two services can communicate seamlessly.

## Getting Started

Follow these instructions to run the application on your local machine.

### Prerequisites

*   **Docker:** [Install Docker](https://docs.docker.com/get-docker/)
*   **Docker Compose:** [Install Docker Compose](https://docs.docker.com/compose/install/)
*   **Kaggle API Key:** You will need to have a `kaggle.json` file with your API credentials to download the dataset. You can create one by following the instructions [here](https://www.kaggle.com/docs/api).

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd mlops/image-class
    ```

2.  **Add Kaggle API Key:**
    *   Create a directory named `kaggle` inside the `mlops/image-class` folder.
    *   Place your `kaggle.json` file inside this new directory.

### Running the Application

1.  **Build and run the containers:**
    From the `mlops/image-class` directory, run the following command:
    ```bash
    docker-compose up --build
    ```
    This command will build the Docker images for the frontend and backend services and start the application.

2.  **Access the Web Interface:**
    Open your web browser and navigate to:
    ```
    http://localhost:8080
    ```
    You can now upload a chest X-ray image to get a prediction.

### Training the Model (Optional)

The notebooks (`cv-aws.ipynb` and `zack-image-classification.ipynb`) contain the code for data preparation and model training.

*   **`zack-image-classification.ipynb`** details the process of training the model locally using PyTorch.
*   **`cv-aws.ipynb`** demonstrates how to leverage **AWS SageMaker** for training, hyperparameter tuning, and deployment. To run this notebook, you will need to have your AWS credentials configured.

The trained model file (`local_image_classifier_model.pth`) is included in the `model-docker` directory, so you do not need to retrain the model to run the application.
