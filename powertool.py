"""Process miner power usage records."""
import datetime
from itertools import chain
from google.cloud import storage

storage_client = storage.Client.from_service_account_json("powermeter.json")
bucket_name = "ethereum_power"
bucket = storage_client.bucket(bucket_name)


def consolidate(name, sources=[]):
    if not name:
        return
    print(color.green + u'\u2192' + color.end,
          color.underline + name + color.end)
    destination = bucket.blob(name)
    destination.content_type = "text/csv"
    destination.compose(sources)


class color:
    cls = '\033c'
    red = '\033[91m'
    yellow = '\033[93m'
    green = '\033[92m'
    blue = '\033[94m'
    bold = '\033[1m'
    underline = '\033[4m'
    end = '\033[0m'


class Level:
    def __init__(self, message, prefix):
        self.message = message
        self.prefix = prefix

    def period(self, name):
        if self.prefix == "records-starting":
            return name.split("T")[0].replace("starting", "daily")
        elif self.prefix == "records-daily":
            return name.rsplit("-", 1)[0].replace("daily", "monthly")
        elif self.prefix == "records-monthly":
            return name.rsplit("-", 1)[0].replace("monthly", "annual")
        else:
            return None


hour2day = Level("Hourly into daily", "records-starting")
day2month = Level("Daily into monthly", "records-daily")
month2year = Level("Monthly into annual", "records-monthly")
levels = [hour2day, day2month, month2year]
print(color.cls + color.bold + "*** Consolidating records ***" + color.end)
for level in levels:
    previous = None
    sources = []
    print(color.blue + level.message + "..." + color.end)
    for blob in storage_client.list_blobs(bucket_name, prefix=level.prefix):
        period = level.period(blob.name)
        if period != previous:
            consolidate(previous, sources)
            previous = period
            sources = [bucket.get_blob(blob.name)]
            print(u'\u2713', blob.name)
        else:
            sources.append(bucket.get_blob(blob.name))
            print(u'\u2713', blob.name)
    else:
        consolidate(previous, sources)

month_now = datetime.datetime.now().month
print(color.bold + "*** Gathering older records to delete ***" + color.end)
blobs_to_delete = []
for blob in chain(
        storage_client.list_blobs(bucket_name, prefix="records-starting"),
        storage_client.list_blobs(bucket_name, prefix="records-daily")):
    if int(blob.name.split("-")[3]) == month_now:
        continue
    print(u'\u274C', blob.name)
    blobs_to_delete.append(bucket.get_blob(blob.name))

if blobs_to_delete:
    confirm = input(color.red + "Confirm deletions (y/N)? " + color.end)
    if confirm.lower() == "y":
        bucket.delete_blobs(blobs_to_delete)
        print("Deletions completed")
    else:
        print("Deletions cancelled")
else:
    print("Nothing to delete")

price = 0.23  # price per kWh in dollars
interval = 5  # duration of record interval in minutes
# TODO: import interval from powermeter
print(color.bold +
      "*** Calculating energy use and costs (${:0.2f} per kWh) ***".format(
          price) + color.end)
for blob in storage_client.list_blobs(bucket_name, prefix="records-monthly"):
    monthly_records = blob.download_as_string().splitlines()
    watts = 0
    for record in monthly_records:
        watts += float(record.split(b",")[2])
    kwh = watts * (interval / 60) / 1000
    cost = kwh * price
    print(blob.name, "\t{:0.4f} kWh\t${:0.2f}".format(kwh, cost))
