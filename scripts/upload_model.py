"""Upload model and feature cache to Azure Blob Storage."""
import os
import joblib
import pandas as pd
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()
conn_str = os.environ['BLOB_CONNECTION_STRING']
container = os.environ.get('BLOB_CONTAINER_NAME', 'ricecast')

client = BlobServiceClient.from_connection_string(conn_str)
cc = client.get_container_client(container)
try:
    cc.create_container()
    print(f"Container '{container}' created.")
except Exception:
    print(f"Container '{container}' already exists.")

with open('models/prophet_model.pkl', 'rb') as f:
    cc.upload_blob('prophet_model.pkl', f, overwrite=True)
print('Uploaded: prophet_model.pkl')

df = pd.read_csv('data/processed/master_df.csv')
tmp_cache = 'feature_cache.csv'
df.tail(24).to_csv(tmp_cache, index=False)
with open(tmp_cache, 'rb') as f:
    cc.upload_blob('feature_cache.csv', f, overwrite=True)
print('Uploaded: feature_cache.csv')
print('Done. Verify in Azure Portal → Storage Account → Containers → ricecast')
