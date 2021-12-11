"""Delete old miner power usage records."""
import datetime
from itertools import chain
from google.cloud import storage

storage_client = storage.Client.from_service_account_json("powermeter.json")
bucket_name = "ethereum_power"
bucket = storage_client.bucket(bucket_name)

month_now = datetime.datetime.now().month

print("\033cGathering old records to delete...")  # with clear screen
blobs_to_delete = []
for blob in chain(
        storage_client.list_blobs(bucket_name, prefix="records-starting"),
        storage_client.list_blobs(bucket_name, prefix="records-daily")):
    if int(blob.name.split("-")[3]) == month_now:
        continue
    print(blob)
    blobs_to_delete.append(bucket.get_blob(blob.name))

confirm = input("Confirm deletion (y/N)? ").lower()
if confirm == "y":
    print("Deleting...")
    bucket.delete_blobs(blobs_to_delete)
    print("Complete")
else:
    print("Cancelled")
