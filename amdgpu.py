from __future__ import print_function
"""Return data via lightweight JSON API."""

import BaseHTTPServer
import urlparse
import json
from os import curdir, sep
import sys
import time
import telnetlib
try:
    import pyadl
    ADL_PRESENT = True
except (ImportError, NameError):
    ADL_PRESENT = False

DEFAULT_SERVER_PORT = 80


def amd_gpu():
    """Return status for each AMD GPU."""
    # derived from https://github.com/nicolargo/pyadl
    if ADL_PRESENT:
        gpu_list = []
        devices = pyadl.ADLManager.getInstance().getDevices()
        for device in devices:
            gpu_status = {}
            gpu_status["adapterIndex"] = device.adapterIndex
            gpu_status["adapterName"] = device.adapterName
            gpu_status["busNumber"] = device.busNumber
            gpu_status["coreVoltageRange"] = device.getCoreVoltageRange()
            gpu_status["coreVoltage"] = device.getCurrentCoreVoltage()
            gpu_status["engineClockRange"] = device.getEngineClockRange()
            gpu_status["engineClock"] = device.getCurrentEngineClock()
            gpu_status["memoryClockRange"] = device.getMemoryClockRange()
            gpu_status["memoryClock"] = device.getCurrentMemoryClock()
            gpu_status["fanSpeedRangePercentage"] = device.getFanSpeedRange(
                pyadl.ADL_DEVICE_FAN_SPEED_TYPE_PERCENTAGE)
            gpu_status["fanSpeedPercentage"] = device.getCurrentFanSpeed(
                pyadl.ADL_DEVICE_FAN_SPEED_TYPE_PERCENTAGE)
            gpu_status["fanSpeedRangeRPM"] = device.getFanSpeedRange(
                pyadl.ADL_DEVICE_FAN_SPEED_TYPE_RPM)
            gpu_status["fanSpeedRPM"] = device.getCurrentFanSpeed(
                pyadl.ADL_DEVICE_FAN_SPEED_TYPE_RPM)
            gpu_status["temperature"] = device.getCurrentTemperature()
            gpu_status["usage"] = device.getCurrentUsage()
            gpu_list.append(gpu_status)
        return {"gpus": gpu_list}
    else:
        return {"error": "AMD Display Library not available"}


def fah_pyon(command, host="localhost"):
    """Retrieve Folding@Home data in PyON format via localhost telnet."""
    # timeout if these cues change because of FAH version change
    timeout = 2
    FAH_TELNET_PORT = 36330
    WELCOME = "Welcome to the FAHClient command server.\n>".encode()
    EXIT = "exit\n".encode()
    HEADER = "PyON 1 ".encode()
    TRAILER = "---\n".encode()
    NEWLINE = "\n".encode()
    tn = telnetlib.Telnet(host, FAH_TELNET_PORT)
    result = tn.read_until(WELCOME, timeout)
    if WELCOME not in result:
        print("Mismatch error starting FAH telnet API")
        sys.stdout.flush()
        return
    tn.write(command.encode() + NEWLINE + EXIT)
    result = tn.read_until(HEADER, timeout)
    if HEADER not in result:
        print("Mismatch error reading FAH telnet API")
        sys.stdout.flush()
        return
    message_name = tn.read_until(NEWLINE, timeout).rstrip().decode()
    output = tn.read_all()
    output = output[:output.find(TRAILER)]
    return {message_name: eval(output, {}, {})}


def fah_gpu():
    """Return F@H status for each gpu."""
    status_dict = {}
    slots = fah_pyon("slot-info")["slots"]
    for slot in slots:
        if "gpu" in slot["description"]:
            gpu = slot["description"].split(":")[1]
            status = slot["status"]
            status_dict[gpu] = status
    print("gpu to status:", status_dict)
    return status_dict


def fah_bus2gpu():
    """Return map from bus to F@H gpu."""
    gpu_dict = {}
    system = fah_pyon("info")["info"][3]
    for item in system:
        if "GPU " in item[0]:
            bus = item[1].split(" ")[0].split(":")[1]
            gpu = item[0].split(" ")[1]
            gpu_dict[bus] = gpu
    print("bus to gpu:", gpu_dict)
    return gpu_dict


def fah_gpu2slot():
    """Return map from F@H gpu to slot."""
    slot_dict = {}
    slots = fah_pyon("slot-info")["slots"]
    for slot in slots:
        if "gpu" in slot["description"]:
            gpu = slot["description"].split(":")[1]
            id = slot["id"]
            slot_dict[gpu] = id
    print("gpu to slot:", slot_dict)
    return slot_dict


class MyHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Handle HTTP get requests."""

    def http_response(self, result):
        """Format and return data function response."""
        if "error" not in list(result.keys()):
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result))
        else:
            self.send_error(400, result["error"])
        sys.stdout.flush()

    def do_GET(self):
        """Respond to a GET request."""
        public_directory = curdir + sep + "amdgpu-public" + sep
        query_string = urlparse.urlparse(self.path).query
        query = urlparse.parse_qs(query_string)
        if "/api/amd/gpu" in self.path:
            self.http_response(amd_gpu())
        elif "/api/fah/bus2gpu" in self.path:
            self.http_response(fah_bus2gpu())
        elif "/api/fah/gpu2slot" in self.path:
            self.http_response(fah_gpu2slot())
        elif "/api/fah/gpu" in self.path:
            self.http_response(fah_gpu())
        else:
            filename = self.path.split("?")[0]
            mode = 'r'
            if filename == "/":
                filename = "index.html"
            print("filename", filename)
            if filename.endswith(".html"):
                mimetype = 'text/html'
            elif filename.endswith(".js"):
                mimetype = 'application/javascript'
            elif filename.endswith(".ico"):
                mimetype = 'image/x-icon'
                mode = 'rb'
            else:
                print("Unknown mimetype for", filename)
            try:
                f = open(public_directory + filename, mode)
                self.send_response(200)
                self.send_header('Content-type', mimetype)
                self.end_headers()
                self.wfile.write(f.read())
                f.close()
                sys.stdout.flush()
            except IOError:
                self.send_error(404)
                sys.stdout.flush()


if __name__ == '__main__':
    try:
        server_port = int(sys.argv[1])
    except (IndexError, ValueError):
        server_port = DEFAULT_SERVER_PORT
    try:
        fh = open(sys.argv[2], "w")
        print("Logging to file", sys.argv[2])
        sys.stdout = fh
        sys.stderr = fh
    except (IndexError):
        print("Logging to console")
    server_class = BaseHTTPServer.HTTPServer
    httpd = server_class(('', server_port), MyHandler)
    print(time.asctime(), "Starting server on port %s" % (server_port))
    sys.stdout.flush()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), "Stopping server on port %s" % (server_port))
    sys.stdout.flush()
