import asyncio
import logging

import requests

from config import CARD_ACTIVATE_URL, CARD_DEACTIVATE_URL, REACTIVATE_DELAY, REQUEST_TIMEOUT

logger = logging.getLogger("printer-client")


def deactivate_card(uid):
    try:
        logger.info(f"Deactivating card: {uid}")
        r = requests.post(CARD_DEACTIVATE_URL, json={"UID": uid}, timeout=REQUEST_TIMEOUT)
        logger.info(f"Deactivate response: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(f"Deactivate failed: {e}")


def activate_card(uid):
    try:
        logger.info(f"Activating card: {uid}")
        r = requests.post(CARD_ACTIVATE_URL, json={"UID": uid}, timeout=REQUEST_TIMEOUT)
        logger.info(f"Activate response: {r.status_code} {r.text}")
    except Exception as e:
        logger.error(f"Activate failed: {e}")


async def reactivate_after_delay(uid):
    logger.info(f"Waiting {REACTIVATE_DELAY}s before reactivating card")
    await asyncio.sleep(REACTIVATE_DELAY)
    activate_card(uid)
