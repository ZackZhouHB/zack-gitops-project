# MLOps Project: Iris Classifier with DVC, MLflow, and Airflow

This project demonstrates a complete MLOps workflow for a simple machine learning task: classifying the Iris dataset. It integrates several key MLOps tools to create a versioned, reproducible, and automated pipeline.

## Project Overview

The goal of this project is to showcase a structured approach to machine learning that goes beyond a simple training script. We use industry-standard tools to manage the entire lifecycle of the model:

*   **Data Versioning:** We use **DVC (Data Version Control)** to track our dataset, ensuring that our experiments are always tied to a specific version of the data.
*   **Experiment Tracking:** **MLflow** is used to log experiments, including model parameters, performance metrics, and the trained model itself. This allows for easy comparison and reproducibility of results.
*   **Pipeline Orchestration:** An **Apache Airflow** DAG is included to demonstrate how the model training process can be automated and scheduled.
*   **Containerization:** The entire project is containerized with **Docker**, making the environment fully reproducible and easy to deploy.

## Core Technologies

*   **Python:** The core programming language.
*   **Scikit-learn:** Used for training the RandomForestClassifier.
*   **DVC:** For data version control.
*   **MLflow:** For experiment tracking and model logging.
*   **Apache Airflow:** For workflow automation and scheduling.
*   **Docker:** For creating a consistent and reproducible environment.

## Project Structure

```
/mlops-project
|-- .dvc/                  # DVC internal files
|-- airflow_dags/          # Airflow DAG for pipeline orchestration
|   `-- ml_pipeline.py
|-- data/
|   |-- .gitignore
|   `-- iris.csv.dvc       # DVC pointer to the dataset
|-- mlruns/                # MLflow tracking data
|-- src/
|   `-- train.py           # Model training script
|-- .dvcignore
|-- Dockerfile             # Docker configuration
|-- dvc.yaml               # DVC pipeline definition (if used)
|-- requirements.txt       # Python dependencies
```

## Workflow

1.  **Data Versioning:** The `data/iris.csv` dataset is tracked by DVC. The `.dvc` file in the `data` directory is a lightweight pointer to the actual data file, which can be stored in a remote location (like S3, GCS, or a shared drive).

2.  **Model Training:** The `src/train.py` script performs the following steps:
    *   Loads the Iris dataset.
    *   Splits the data into training and testing sets.
    *   Initializes an MLflow run to start tracking.
    *   Trains a `RandomForestClassifier`.
    *   Logs the model's accuracy as a metric to MLflow.
    *   Logs the trained model itself as an artifact in MLflow.

3.  **Experiment Tracking:** Every time `src/train.py` is run, a new experiment is logged in the `mlruns` directory. You can inspect these runs, compare metrics, and view the saved models using the MLflow UI.

4.  **Orchestration:** The `airflow_dags/ml_pipeline.py` file defines a simple Airflow DAG that automates the execution of the training script. This can be used to schedule regular retraining of the model.

## Getting Started

### Prerequisites

*   **Python 3.10+**
*   **Docker** and **Docker Compose**
*   **DVC:** `pip install dvc`
*   **MLflow:** `pip install mlflow`

### Setup and Running

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd mlops/mlops-project
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Pull the Data:**
    Initialize DVC to retrieve the dataset. If you have a remote storage configured, DVC will pull the data from there. For this local example, you may need to place the `iris.csv` file in the `data` directory manually if it's not already present.
    ```bash
    dvc pull
    ```

4.  **Run the Training Script:**
    Execute the training script to train the model and log the experiment with MLflow.
    ```bash
    python src/train.py
    ```
    You should see an output indicating the model's accuracy.

5.  **View Experiments with MLflow:**
    Launch the MLflow UI to see the results of your training run.
    ```bash
    mlflow ui
    ```
    Open your browser and navigate to `http://localhost:5000`. You will find your experiment, including the logged accuracy and the saved model.

6.  **Run with Docker (Optional):**
    You can also build and run the training process inside a Docker container for a fully isolated environment.
    ```bash
    docker build -t mlops-iris-app .
    docker run mlops-iris-app
    ```

### Airflow Orchestration (Advanced)

To run the automated pipeline with Airflow, you would need to set up an Airflow environment and add the `ml_pipeline.py` DAG to your Airflow DAGs folder. This is an advanced step that demonstrates how this project can be integrated into a larger automated MLOps system.
