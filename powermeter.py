"""Record miner power usage."""
import sys
import datetime
import time
import requests
from google.cloud import storage

miner_url = "http://capitola.larrylang.net/api/eth/gpu"
interval = 5  # minutes

storage_client = storage.Client.from_service_account_json('powermeter.json')
bucket_name = "ethereum_power"
bucket = storage_client.bucket(bucket_name)

try:
    fh = open(sys.argv[1], "w")
    print("Logging to file", sys.argv[1])
    sys.stdout = fh
    sys.stderr = fh
except (IndexError):
    print("Logging to console")

previous_epoch = -1  # first pass force open
while True:
    date_now_iso = datetime.datetime.now().replace(microsecond=0).isoformat()
    epoch = datetime.datetime.now().hour  # .minute .day
    if epoch != previous_epoch:
        try:
            gcs_file.close()
        except NameError:
            pass  # first pass nothing to close
        blob = bucket.blob("records-starting-" + date_now_iso)
        gcs_file = blob.open("wt", content_type="text/csv")
        print(date_now_iso, "starting new file")
        sys.stdout.flush()
        previous_epoch = epoch
    record = date_now_iso + ","
    gpus = requests.get(url=miner_url).json()["DEVS"]
    record += str(len(gpus)) + ","
    power = 0
    for gpu in gpus:
        power += gpu["GPU Power"]
    record += str(power)
    print(record)
    sys.stdout.flush()
    gcs_file.write(record + "\n")
    try:
        sleep_duration = 60 * (interval - datetime.datetime.now().minute %
                               interval) - datetime.datetime.now().second
    except ZeroDivisionError:
        sleep_duration = 10
    time.sleep(sleep_duration)
