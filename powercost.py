"""Calculate monthly costs from miner power usage records."""

from google.cloud import storage

storage_client = storage.Client.from_service_account_json("powermeter.json")
bucket_name = "ethereum_power"
bucket = storage_client.bucket(bucket_name)

price = 0.23  # price per kWh in dollars
interval = 5  # duration of record interval in minutes

print("\033cCalculating monthly power costs (${:0.2f} per kWh)...".format(price)) # with clear screen
blobs_to_delete = []
for blob in storage_client.list_blobs(bucket_name, prefix="records-monthly"):
    monthly_records = blob.download_as_string().splitlines()
    watts = 0
    for record in monthly_records:
        watts += float(record.split(b",")[2])
    kwh = watts * (interval/60) / 1000
    print(blob.name, "\t{:0.4f} kWh".format(kwh), "\t${:0.2f}".format(price*kwh))
