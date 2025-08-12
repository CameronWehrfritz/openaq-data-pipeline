# Test GCP connection

from dotenv import load_dotenv, find_dotenv
import os
from google.cloud import bigquery

# 1️⃣ Ensure .env exists and load it
env_path = find_dotenv()
if not env_path:
    raise FileNotFoundError("❌ .env file not found! Make sure it exists in your project folder.")

print(f"✅ .env file found at: {env_path}")
load_dotenv(env_path)

# 2️⃣ Ensure GOOGLE_APPLICATION_CREDENTIALS is set
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not creds_path:
    raise EnvironmentError("❌ GOOGLE_APPLICATION_CREDENTIALS is not set in your .env file.")

# 3️⃣ Ensure key file exists
if not os.path.exists(creds_path):
    raise FileNotFoundError(f"❌ Credential file not found at: {creds_path}")

print(f"✅ Found GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")

# 4️⃣ Try connecting to BigQuery
try:
    client = bigquery.Client()
    datasets = list(client.list_datasets())
    if datasets:
        print("✅ Connected to BigQuery! Available datasets:")
        for dataset in datasets:
            print(f" - {dataset.dataset_id}")
    else:
        print("✅ Connected to BigQuery, but no datasets found.")
except Exception as e:
    raise ConnectionError(f"❌ Could not connect to BigQuery: {e}")
