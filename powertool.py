"""Process miner power usage records on Google Cloud Storage."""
import datetime
from itertools import chain

from google.cloud import storage

import powermeter

storage_client = storage.Client.from_service_account_json("powermeter.json")
bucket_name = "ethereum_power"
bucket = storage_client.bucket(bucket_name)

interval = powermeter.interval
price_kwh = 0.23


def list(blobprefix):
    """List GCS blobs with prefix."""
    return storage_client.list_blobs(bucket_name, prefix=blobprefix)


def compose(blobname, sources=[]):
    """Compose new GCS blob from list of source blobs."""
    if not blobname:
        return
    print(TTY.green + u'\u2192' + TTY.end, TTY.underline + blobname + TTY.end)
    destination = bucket.blob(blobname)
    destination.content_type = "text/csv"
    destination.compose(sources)


class TTY:
    """ASCII terminal escape sequences."""

    cls = '\033c'
    bold = '\033[1m'
    underline = '\033[4m'
    red = '\033[91m'
    green = '\033[92m'
    blue = '\033[94m'
    end = '\033[0m'


class LevelStep:
    """Step from one interval to the next-longer interval."""

    def __init__(self, message, prefix):
        """Provide interface message and blob prefix for each interval."""
        self.message = message
        self.prefix = prefix

    def period(self, name):
        """Format blobname for next-longer interval."""
        if self.prefix == "records-starting":
            return name.split("T")[0].replace("starting", "daily")
        elif self.prefix == "records-daily":
            return name.rsplit("-", 1)[0].replace("daily", "monthly")
        elif self.prefix == "records-monthly":
            return name.rsplit("-", 1)[0].replace("monthly", "annual")
        else:
            return None


def consolidate():
    """Consolidate records into longer intervals."""
    hour2day = LevelStep("Hourly into daily", "records-starting")
    day2month = LevelStep("Daily into monthly", "records-daily")
    month2year = LevelStep("Monthly into annual", "records-monthly")
    levels = [hour2day, day2month, month2year]
    print(TTY.cls + TTY.bold + "*** Consolidating records ***" + TTY.end)
    for level in levels:
        previous = None
        sources = []
        print(TTY.blue + level.message + "..." + TTY.end)
        for blob in list(level.prefix):
            period = level.period(blob.name)
            if period != previous:
                compose(previous, sources)
                previous = period
                sources = [bucket.get_blob(blob.name)]
                print(u'\u2713', blob.name)
            else:
                sources.append(bucket.get_blob(blob.name))
                print(u'\u2713', blob.name)
        else:
            compose(previous, sources)


def delete():
    """Delete hourly and daily records from previous months."""
    month_now = datetime.datetime.now().month
    print(TTY.bold + "*** Gathering older records to delete ***" + TTY.end)
    blobs_to_delete = []
    for blob in chain(list("records-starting"), list("records-daily")):
        if int(blob.name.split("-")[3]) == month_now:
            continue
        print(u'\u274C', blob.name)
        blobs_to_delete.append(bucket.get_blob(blob.name))

    if blobs_to_delete:
        confirm = input(TTY.red + "Confirm deletions (y/N)? " + TTY.end)
        if confirm.lower() == "y":
            bucket.delete_blobs(blobs_to_delete)
            print("Deletions completed")
        else:
            print("Deletions cancelled")
    else:
        print("Nothing to delete")


def energy(interval, price):
    """Calculate energy use and cost.

    interval: record duration in minutes
    price: per kWh in dollars
    """
    print(TTY.bold +
          "*** Calculating energy use and costs at ${:0.2f} per kWh ***".
          format(price) + TTY.end)
    for blob in list("records-monthly"):
        monthly_records = blob.download_as_string().splitlines()
        watts = 0
        for record in monthly_records:
            watts += float(record.split(b",")[2])
        kwh = watts * (interval / 60) / 1000
        cost = kwh * price
        print(blob.name, "\t{:0.4f} kWh\t${:0.2f}".format(kwh, cost))


if __name__ == "__main__":
    consolidate()
    delete()
    energy(interval, price_kwh)
