from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime
import os

# Define your DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1),
    'retries': 1,
}

dag = DAG('mlops_pipeline', default_args=default_args, schedule_interval='@daily')

# Define the task to retrain the model
def retrain_model():
    os.system('python src/train.py')

retrain_task = PythonOperator(
    task_id='retrain_model',
    python_callable=retrain_model,
    dag=dag
)

retrain_task

