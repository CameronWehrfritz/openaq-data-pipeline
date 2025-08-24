# Test GCP connection

from dotenv import load_dotenv, find_dotenv
import os
from google.cloud import bigquery

# 1. Ensure .env exists and load it
env_path = find_dotenv()
if not env_path:
    raise FileNotFoundError("ERROR: .env file not found! Make sure it exists in your project folder.")

print(f"INFO: .env file found at: {env_path}")
load_dotenv(env_path)

# 2. Ensure GOOGLE_APPLICATION_CREDENTIALS is set
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not creds_path:
    raise EnvironmentError("ERROR: GOOGLE_APPLICATION_CREDENTIALS is not set in your .env file.")

# 3. Ensure key file exists
if not os.path.exists(creds_path):
    raise FileNotFoundError(f"ERROR: Credential file not found at: {creds_path}")

print(f"SUCCESS: Found GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")

# 4. Try connecting to BigQuery
try:
    client = bigquery.Client()
    datasets = list(client.list_datasets())
    if datasets:
        print("SUCCESS: Connected to BigQuery! Available datasets:")
        for dataset in datasets:
            print(f" - {dataset.dataset_id}")
    else:
        print("SUCCESS: Connected to BigQuery, but no datasets found.")
except Exception as e:
    raise ConnectionError(f"ERROR: Could not connect to BigQuery: {e}")
