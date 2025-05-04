FROM apache/airflow:2.7.3-python3.10

USER root
COPY requirements.txt /requirements.txt
RUN chown airflow: /requirements.txt

# Adjust these paths to your project structure
COPY dags/           /opt/airflow/dags/
COPY ingestion/      /opt/airflow/ingestion/

# Set ownership so airflow user can read/write
RUN chown -R airflow: /opt/airflow/dags \
    && chown -R airflow: /opt/airflow/ingestion

USER airflow
RUN pip install --no-cache-dir -r /requirements.txt