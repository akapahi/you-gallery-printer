import asyncio
import json
import logging
import signal

import requests
import websockets

from card import deactivate_card, reactivate_after_delay
from config import RECONNECT_DELAY, REQUEST_TIMEOUT, STATION_ID, VISITOR_API, WS_URL, DEBUG
from health import send_health_ping
from renderer import generate_test_print, is_empty, print_visitor_ticket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    force=True,
)
logger = logging.getLogger("printer-client")

_printer = None


def fetch_visitor_data(uid):
    try:
        logger.info(f"Fetching visitor data for UID: {uid}")
        r = requests.get(VISITOR_API, json={"UID": uid}, timeout=REQUEST_TIMEOUT)
        logger.info(f"Visitor API status: {r.status_code}")

        data     = r.json()
        app_data = data.get("appData")

        logger.info(json.dumps(data, indent=2))

        if not app_data or is_empty(app_data):
            logger.info("No appData found, skipping print")
            return

        if not DEBUG:
            deactivate_card(uid)
        else:
            logger.info("[DEBUG] Skipping card deactivation")

        print_visitor_ticket(_printer, data)
        asyncio.get_running_loop().create_task(reactivate_after_delay(uid))

    except requests.RequestException as e:
        logger.error(f"Visitor API request failed: {e}")
    except Exception as e:
        logger.error(f"Visitor data processing failed: {e}")


def process_message(message):
    try:
        doc        = json.loads(message).get("doc", {})
        event_type = doc.get("eventType")
        station_id = doc.get("stationId")
        uid        = doc.get("UID")

        logger.info(f"Event: {event_type} | Station: {station_id} | UID: {uid}")

        if event_type == "cardDetected" and station_id == STATION_ID and uid:
            logger.info(f"Printer card detected: {uid}")
            fetch_visitor_data(uid)

    except json.JSONDecodeError:
        logger.warning("Invalid websocket JSON")
    except Exception as e:
        logger.error(f"Message processing error: {e}")


async def websocket_loop():
    while True:
        try:
            logger.info(f"Connecting to {WS_URL}")
            async with websockets.connect(WS_URL) as ws:
                logger.info("Connected — waiting for messages...")
                async for message in ws:
                    logger.info(f"Raw message: {message}")
                    process_message(message)
        except Exception as e:
            logger.error(f"Websocket error: {e}")

        logger.info(f"Reconnecting in {RECONNECT_DELAY}s...")
        await asyncio.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    from escpos.printer import Usb

    logger.info("=" * 32)
    logger.info("Printer WebSocket Client Started")
    logger.info("=" * 32)

    try:
        _printer = Usb(0x0483, 0x5743, in_ep=0x81, out_ep=0x01)
        logger.info("Printer connected")
        send_health_ping()
    except Exception as e:
        logger.error(f"Printer init failed: {e}")

    def _on_test_print():
        logger.info("SIGUSR1 received — running test print")
        generate_test_print(_printer)

    loop = asyncio.new_event_loop()
    loop.add_signal_handler(signal.SIGUSR1, _on_test_print)
    loop.run_until_complete(websocket_loop())
