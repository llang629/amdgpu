"""Consolidate miner power usage records."""
import pprint
from google.cloud import storage

storage_client = storage.Client.from_service_account_json("powermeter.json")
bucket_name = "ethereum_power"
bucket = storage_client.bucket(bucket_name)

print("\033cConsolidating hourly into daily...")  # with clear screen
daily_sources = {}
for blob in storage_client.list_blobs(bucket_name, prefix="records-starting"):
    day = blob.name.split("T")[0].replace("starting", "daily")
    try:
        daily_sources[day].append(bucket.get_blob(blob.name))
    except KeyError:
        daily_sources[day] = [bucket.get_blob(blob.name)]
pprint.pprint(daily_sources)
for day in daily_sources:
    destination = bucket.blob(day)
    destination.content_type = "text/csv"
    destination.compose(daily_sources[day])

print("Consolidating daily into monthly...")
monthly_sources = {}
for blob in storage_client.list_blobs(bucket_name, prefix="records-daily"):
    month = blob.name.rsplit("-", 1)[0].replace("daily", "monthly")
    try:
        monthly_sources[month].append(bucket.get_blob(blob.name))
    except KeyError:
        monthly_sources[month] = [bucket.get_blob(blob.name)]
pprint.pprint(monthly_sources)
for month in monthly_sources:
    destination = bucket.blob(month)
    destination.content_type = "text/csv"
    destination.compose(monthly_sources[month])

print("Consolidating monthly into annual...")
annual_sources = {}
for blob in storage_client.list_blobs(bucket_name, prefix="records-monthly"):
    year = blob.name.rsplit("-", 1)[0].replace("monthly", "annual")
    print(year)
    try:
        annual_sources[year].append(bucket.get_blob(blob.name))
    except KeyError:
        annual_sources[year] = [bucket.get_blob(blob.name)]
pprint.pprint(annual_sources)
for year in annual_sources:
    destination = bucket.blob(year)
    destination.content_type = "text/csv"
    destination.compose(annual_sources[year])
