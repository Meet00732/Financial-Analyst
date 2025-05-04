import re
from bs4 import BeautifulSoup
import time
import pandas as pd
import requests
import json
import boto3
from botocore.exceptions import ClientError
from functools import lru_cache

_PATTERNS = {
    'business': re.compile(r"Item\s+1\.\s+Business(.*?)(?=Item\s+1A\.)", re.IGNORECASE | re.DOTALL),
    'risk_factors': re.compile(r"Item\s+1A\.\s+Risk Factors(.*?)(?=Item\s+1B\.)", re.IGNORECASE | re.DOTALL),
    'mdna': re.compile(r"Item\s+7\.\s+Management.*?Discussion.*?(.*?)(?=Item\s+7A\.)", re.IGNORECASE | re.DOTALL),
}

def extract_sections(html_text: str) -> dict[str, str]:
    """
    Parse HTML and extract key sections using precompiled patterns.
    """
    text = BeautifulSoup(html_text, 'lxml').get_text()
    sections = {}
    for key, pattern in _PATTERNS.items():
        m = pattern.search(text)
        if m:
            sections[key] = m.group(1).strip()
    return sections


def get_sp500_tickers(top_n: int = 10) -> list[str]:
    """
    Scrape S&P 500 tickers from Wikipedia once per run.
    """
    time.sleep(0.5)
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "MarketScopeBot/1.0"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    df = pd.read_html(resp.text, flavor='bs4')[0]
    tickers = df['Symbol'].str.replace('.', '-', regex=False).tolist()
    return tickers[:top_n]



@lru_cache(maxsize=None)
def get_secret(secret_name: str, region_name: str = "us-east-1") -> str:
    """
    Fetches and returns the secret value from AWS Secrets Manager.

    Caches results to avoid repeated network calls.

    If the secret is a JSON string, returns the raw string; the caller
    can json.loads() as needed.

    Args:
        secret_name: Name or ARN of the secret in AWS Secrets Manager.
        region_name: AWS region where the secret is stored.

    Returns:
        SecretString from Secrets Manager.

    Raises:
        ClientError: If the secret retrieval fails.
    """
    client = boto3.client("secretsmanager", region_name=region_name)
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # Re-raise exception for the caller to handle/log
        raise e

    if "SecretString" in response:
        return response["SecretString"]
    else:
        # Secret is binary
        decoded_binary = response["SecretBinary"]
        # If caller needs binary, they can base64 decode 
        return decoded_binary