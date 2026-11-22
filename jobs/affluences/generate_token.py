import logging
import os

import requests
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

load_dotenv()

ANDROID_DEVICE_ID = os.getenv("ANDROID_DEVICE_ID", "12345678abcdefgh")
ANDROID_DEVICE_LANG = os.getenv("ANDROID_DEVICE_LANG", "en")
ANDROID_DEVICE_USER_AGENT = os.getenv("ANDROID_DEVICE_USER_AGENT", "Affluences/202606010 (Android; 15)")
ANDROID_APP_VERSION = os.getenv("ANDROID_APP_VERSION", "202606010")


AFFLUENCES_FIREBASE_TOKEN = "c6f9O60KRmylazDl6583aO:APA91bGbkLis52sKlaPBcJc8otq0T9dW-XQA8BfLLTN_GMGjGu3YB3CyKWcEyg3zW3OlV2XtasD2tFhOKzlPoI_qLGNH-wWIkdE0o98U-Sv2pIo18afkNlk"

def generate_affluences_token():
    url = "https://api.affluences.com/app/v4/apps/checkin"

    payload = {
        "deviceId": ANDROID_DEVICE_ID,
        "deviceLang": ANDROID_DEVICE_LANG,
        "lastCheckin": None,
        "lastCheckinAdvertPopup": None,
        "firebaseToken": AFFLUENCES_FIREBASE_TOKEN,
    }
    headers = {
        "user-agent": ANDROID_DEVICE_USER_AGENT,
        "accept-language": ANDROID_DEVICE_LANG,
        "accept-encoding": "gzip",
        "host": "api.affluences.com",
        "x-service-name": "mobile_app",
        "content-type": "application/json",
        "x-device-type": "android",
        "x-app-version": ANDROID_APP_VERSION,
    }

    log.info("Generating Affluences token...")

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        log.info(data)
        api_token = data.get("data", {}).get("apiKey", "")
        return api_token
    except requests.exceptions.RequestException as e:
        log.error("Errore API")
        return None


if __name__ == '__main__':
    token = generate_affluences_token()
    log.info("Token: %s", token)
    if(token):
        with open(".affluences_token", "w") as f:
            f.write(token)
