import requests
import time

from config import TELEGRAM_TOKEN

API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"


def send(chat_id, text, buttons=None, keyboard=None):

    url = f"{API}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": buttons
        }

    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(url, json=payload)


def send_photo(chat_id, photo, caption=None):

    url = f"{API}/sendPhoto"

    payload = {
        "chat_id": chat_id,
        "photo": photo
    }

    if caption:
        payload["caption"] = caption

    requests.post(url, json=payload)


def thinking(chat_id):

    url = f"{API}/sendChatAction"

    payload = {
        "chat_id": chat_id,
        "action": "typing"
    }

    requests.post(url, json=payload)

    time.sleep(0.4)