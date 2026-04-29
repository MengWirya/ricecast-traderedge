import os
import json
import pandas as pd
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
 
load_dotenv()  # loads .env from project root
 
CONN_STR  = os.environ["BLOB_CONNECTION_STRING"]
CONTAINER = os.environ.get("BLOB_CONTAINER_NAME", "ricecast")
 
client = BlobServiceClient.from_connection_string(CONN_STR)
 
# Create container if it doesn't exist yet
try:
    client.create_container(CONTAINER)
    print(f"Container '{CONTAINER}' created")
except Exception:
    print(f"Container '{CONTAINER}' already exists — OK")
 
 
def upload(local_path: str, blob_name: str):
    with open(local_path, "rb") as f:
        client.get_blob_client(CONTAINER, blob_name).upload_blob(f, overwrite=True)
    size_kb = os.path.getsize(local_path) / 1024
    print(f"  ✓ Uploaded {local_path} → {blob_name}  ({size_kb:.0f} KB)")
 
 
print("\nUploading files to Azure Blob Storage...")
 
# 1. Prophet model
upload("models/prophet_model.pkl", "prophet_model.pkl")
 
# 2. master_df sample — last 36 rows (enough for feature lookup, safe to upload)
df = pd.read_csv("data/processed/master_df.csv", parse_dates=["ds"])
sample = df.tail(36)
sample_path = "/tmp/master_df_sample.csv"
sample.to_csv(sample_path, index=False)
upload(sample_path, "master_df_sample.csv")
 
# 3. current_price.json (built in Cell 8 of 01_master_df.py)
if os.path.exists("data/processed/current_price.json"):
    upload("data/processed/current_price.json", "current_price.json")
else:
    # Build it now from the last row of master_df
    last_row = df.iloc[-1]
    current_price_info = {
        "current_price": float(last_row["y"]),
        "source":        "master_df last row",
        "date":          str(last_row["ds"].date()),
    }
    tmp_path = "/tmp/current_price.json"
    with open(tmp_path, "w") as f:
        json.dump(current_price_info, f, indent=2)
    upload(tmp_path, "current_price.json")
    print(f"     current_price: Rp {current_price_info['current_price']:,.0f}")
 
print("\nAll files uploaded. Ready to deploy Azure Function.")
print(f"Blob container: https://portal.azure.com → Storage accounts → {CONTAINER}")