# Dockerfile
FROM apache/airflow:2.7.1

USER root

# install Python libs for EdgarTools, yfinance, scraping, etc.
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# copy your DAG and modules into Airflow's filesystem
COPY dags/ /opt/airflow/dags/
COPY ingestion/ /opt/airflow/ingestion/

USER airflow
