"""
storage.py

Storage utilities for MarketScope pipeline.
Retrieves S3 bucket name from Secrets Manager and stores data under organized prefixes.
"""
import io
import json
import boto3
import pandas as pd
from botocore.exceptions import ClientError
from utils.secrets_utils import get_secret

# Secret name in AWS Secrets Manager holding the S3 bucket name
_BUCKET_SECRET_NAME = "marketscope-BUCKET_NAME"

# Lazy-load S3 bucket name
_s3_bucket = None

def _get_bucket() -> str:
    global _s3_bucket
    if not _s3_bucket:
        _s3_bucket = get_secret(_BUCKET_SECRET_NAME)
    return _s3_bucket

# Build object key under given prefix
def _key(prefix: str, filename: str) -> str:
    return f"{prefix}/{filename}"

# Initialize S3 client
_s3 = boto3.client("s3")


def save_filings(filings: list[dict]):
    """
    Save SEC filings (sections + xbrl_facts) as JSON per ticker in S3 under 'filings/'.
    """
    bucket = _get_bucket()
    for doc in filings:
        ticker = doc.get("ticker")
        date = doc.get("filing_date")
        key = _key("filings", f"{ticker}_{date}.json")
        body = json.dumps(doc, indent=2, default=str).encode('utf-8')
        _s3.put_object(Bucket=bucket, Key=key, Body=body)


def save_market_data(ticker: str, market_data: dict):
    """
    Save market data: history as Parquet and fundamentals as JSON in S3 under 'market/'.
    """
    bucket = _get_bucket()
    # History DataFrame -> Parquet bytes
    hist: pd.DataFrame = market_data.get("history")
    hist_buffer = io.BytesIO()
    hist.to_parquet(hist_buffer, index=True)
    hist_buffer.seek(0)
    hist_key = _key("market/history", f"{ticker}_history.parquet")
    _s3.upload_fileobj(hist_buffer, bucket, hist_key)

    # Fundamentals dict -> JSON
    fund = market_data.get("fundamentals")
    fund_body = json.dumps(fund, indent=2, default=str).encode('utf-8')
    fund_key = _key("market/fundamentals", f"{ticker}_fundamentals.json")
    _s3.put_object(Bucket=bucket, Key=fund_key, Body=fund_body)


def save_combined(filings: list[dict]):
    """
    Save combined filings + market_data list as a single JSON in S3 under 'combined/'.
    """
    bucket = _get_bucket()
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    key = _key("combined", f"combined_{timestamp}.json")
    body = json.dumps(filings, indent=2, default=str).encode('utf-8')
    _s3.put_object(Bucket=bucket, Key=key, Body=body)


def load_history(ticker: str) -> pd.DataFrame:
    """
    Load market history DataFrame for a ticker from S3.
    """
    bucket = _get_bucket()
    key = _key("market/history", f"{ticker}_history.parquet")
    obj = _s3.get_object(Bucket=bucket, Key=key)
    return pd.read_parquet(io.BytesIO(obj['Body'].read()))


def load_fundamentals(ticker: str) -> dict:
    """
    Load market fundamentals JSON for a ticker from S3.
    """
    bucket = _get_bucket()
    key = _key("market/fundamentals", f"{ticker}_fundamentals.json")
    obj = _s3.get_object(Bucket=bucket, Key=key)
    return json.loads(obj['Body'].read().decode('utf-8'))












# # storage.py
# """
# Storage utilities for MarketScope pipeline.
# Provides functions to save SEC filings, XBRL facts, market data, and combined outputs.
# """
# import os
# import json
# import pandas as pd

# # Directory paths (can be parameterized)
# DATA_DIR = "./data"
# FILINGS_DIR = os.path.join(DATA_DIR, "filings")
# MARKET_DIR = os.path.join(DATA_DIR, "market")
# COMBINED_DIR = os.path.join(DATA_DIR, "combined")

# # Ensure directories exist
# for d in (FILINGS_DIR, MARKET_DIR, COMBINED_DIR):
#     os.makedirs(d, exist_ok=True)


# def save_filings(filings: list[dict]):
#     """
#     Save SEC filings (sections + xbrl_facts) as JSON per ticker.
#     """
#     for doc in filings:
#         ticker = doc.get("ticker")
#         path = os.path.join(FILINGS_DIR, f"{ticker}_{doc.get('filing_date')}.json")
#         with open(path, "w", encoding="utf-8") as f:
#             json.dump(doc, f, indent=2, default=str)


# def save_market_data(ticker: str, market_data: dict):
#     """
#     Save market data: history as Parquet, fundamentals as JSON.
#     """
#     # Save history DataFrame
#     hist = market_data.get("history")
#     hist_path = os.path.join(MARKET_DIR, f"{ticker}_history.parquet")
#     # history is a DataFrame
#     hist.to_parquet(hist_path)

#     # Save fundamentals dict
#     fund = market_data.get("fundamentals")
#     fund_path = os.path.join(MARKET_DIR, f"{ticker}_fundamentals.json")
#     with open(fund_path, "w", encoding="utf-8") as f:
#         json.dump(fund, f, indent=2, default=str)


# def save_combined(filings: list[dict]):
#     """
#     Save combined filings + market_data list as single JSON.
#     """
#     timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
#     path = os.path.join(COMBINED_DIR, f"combined_{timestamp}.json")
#     with open(path, "w", encoding="utf-8") as f:
#         json.dump(filings, f, indent=2, default=str)


# def load_history(ticker: str) -> pd.DataFrame:
#     """
#     Load market history DataFrame for a ticker.
#     """
#     hist_path = os.path.join(MARKET_DIR, f"{ticker}_history.parquet")
#     return pd.read_parquet(hist_path)


# def load_fundamentals(ticker: str) -> dict:
#     """
#     Load market fundamentals JSON for a ticker.
#     """
#     fund_path = os.path.join(MARKET_DIR, f"{ticker}_fundamentals.json")
#     with open(fund_path, "r", encoding="utf-8") as f:
#         return json.load(f)



