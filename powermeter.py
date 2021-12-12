"""Record miner power usage."""
import datetime
import signal
import sys
import time

import requests
from google.cloud import storage

storage_client = storage.Client.from_service_account_json("powermeter.json")
bucket_name = "ethereum_power"
bucket = storage_client.bucket(bucket_name)

miner_url = "http://capitola.larrylang.net/api/eth/gpu"
interval = 5  # minutes between records


class SysSignals:
    """Catch system signals."""

    def __init__(self):
        """Prepare to catch signals from local operating system."""
        catchable_signals = set(signal.Signals)
        if sys.platform == "darwin":
            catchable_signals -= {signal.SIGKILL, signal.SIGSTOP}
        elif sys.platform == "win32":
            catchable_signals -= {signal.CTRL_C_EVENT, signal.CTRL_BREAK_EVENT}
        else:
            print("Untested system")
            sys.stdout.flush()
            sys.exit(1)

        for sig in catchable_signals:
            print("Catching", sig)
            sys.stdout.flush()
            signal.signal(sig, self.handler)

    def handler(self, signum, frame):
        """Handle system signals."""
        # TODO: catch signal from Windows Task Scheduler
        # TODO: close Google Cloud Storage file gracefully
        print("Signal Number:", signum, " Frame: ", frame)
        sys.stdout.flush()
        sys.exit(signum)


def record(url, interval):
    """Record GPU power consumption every interval."""
    previous_epoch = -1  # first pass force open
    while True:
        date_now_iso = datetime.datetime.now().replace(
            microsecond=0).isoformat()
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
        gpu_count = 0
        gpu_power = 0
        try:
            gpus = requests.get(url=url, timeout=10).json()["DEVS"]
            gpu_count = len(gpus)
            for gpu in gpus:
                gpu_power += gpu["GPU Power"]
        except (requests.exceptions.RequestException, ValueError):
            pass  # api fails to respond or response json invalid
        record = date_now_iso + ","
        record += str(gpu_count) + ","
        record += str(gpu_power)
        print(record)
        sys.stdout.flush()
        gcs_file.write(record + "\n")
        try:
            sleep_duration = 60 * (interval - datetime.datetime.now().minute %
                                   interval) - datetime.datetime.now().second
        except ZeroDivisionError:
            sleep_duration = 10
        time.sleep(sleep_duration)


if __name__ == "__main__":
    try:
        fh = open(sys.argv[1], "w")
        print("Logging to file", sys.argv[1])
        sys.stdout = fh
        sys.stderr = fh
    except (IndexError):
        print("Logging to console")

    syssig = SysSignals()
    record(miner_url, interval)
