import json
import logging
import platform
import shutil
import socket
import uuid

import requests

from config import DEVICE_TYPE, HEALTH_URL, REQUEST_TIMEOUT, STATION_ID

logger = logging.getLogger("printer-client")


def get_mac_address():
    mac_num = hex(uuid.getnode())[2:].zfill(12)
    return ":".join(mac_num[i:i+2] for i in range(0, 12, 2))


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "unknown"


def send_health_ping():
    payload = {
        "type":      DEVICE_TYPE,
        "stationId": STATION_ID,
        "status":    "ok",
        "metrics": {
            "freeDiskMB": round(shutil.disk_usage("/").free / 1024 / 1024, 2),
        },
        "errors": [],
        "meta": {
            "ip":              get_local_ip(),
            "mac":             get_mac_address(),
            "hostname":        socket.gethostname(),
            "platform":        platform.platform(),
            "pythonVersion":   platform.python_version(),
            "firmwareVersion": "python-client-1.0",
        },
    }

    try:
        logger.info("Sending health ping...")
        logger.info(json.dumps(payload, indent=2))
        r = requests.post(HEALTH_URL, json=payload, timeout=REQUEST_TIMEOUT)
        logger.info(f"Health ping response: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(f"Health ping failed: {e}")
