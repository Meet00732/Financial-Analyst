from datetime import datetime, timedelta
import json

from airflow import DAG
from airflow.operators.python import PythonOperator

from ingestion.edgar_ingestor.fetch_filings import *
from ingestion.edgar_ingestor.storage import *

default_args = {
    "owner": "meet",
    "depends_on_past": False,
    "start_date": datetime(2025, 5, 5),
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="market_scope_ingest",
    default_args=default_args,
    schedule_interval="@daily",
    catchup=False,
    tags=["market_scope", "rag"],
) as dag:
    
    def ingest_filings(**kwargs):
        filings = fetch_edgar_filings(form_type="10-K", top_n=10)
        save_filings(filings)
        # push to XCom for downstream tasks
        kwargs["ti"].xcom_push(key="filings", value=filings)

    def ingest_market(**kwargs):
        filings = kwargs["ti"].xcom_pull(key="filings", task_ids="ingest_filings")
        for doc in filings:
            ticker = doc["ticker"]
            mdata = fetch_market_data(ticker)
            save_market_data(ticker, mdata)
            doc["market_data"] = {
                "fundamentals": mdata["fundamentals"],
                "recent_history": mdata["history"].tail().to_dict(orient="list"),
            }
        kwargs["ti"].xcom_push(key="enriched", value=filings)

    def finalize(**kwargs):
        enriched = kwargs["ti"].xcom_pull(key="enriched", task_ids="ingest_market")
        save_combined(enriched)

    ingest_task = PythonOperator(
        task_id="ingest_filings",
        python_callable=ingest_filings,
        provide_context=True,
    )

    market_task = PythonOperator(
        task_id="ingest_market",
        python_callable=ingest_market,
        provide_context=True,
    )

    finalize_task = PythonOperator(
        task_id="finalize",
        python_callable=finalize,
        provide_context=True,
    )

    ingest_task >> market_task >> finalize_task