import requests
import time
import random

from flask import Flask, request

from config import TOKEN
from data import load_data
from catalog import get_categories, get_types, get_products
from recipes import recipes_by_ingredient, get_recipe
from stock import get_product, set_product, get_all
from translations import format_product_name
from utils import emoji_for_product, extract_taste_emojis
from nlp_food import extract_ingredients

from phrases import THINKING, FOUND, NOT_FOUND, ACTION, COOK, phrase


app = Flask(__name__)

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"

user_state = {}

# ================= TELEGRAM =================


def send(chat_id, text, keyboard=None):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(f"{TELEGRAM_URL}/sendMessage", json=payload)


def edit(chat_id, message_id, text, keyboard=None):

    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(f"{TELEGRAM_URL}/editMessageText", json=payload)


# ================= KEYBOARDS =================


def reply_keyboard(rows):

    return {
        "keyboard": rows,
        "resize_keyboard": True
    }


def inline_keyboard(rows):

    return {
        "inline_keyboard": rows
    }


# ================= LIVE RESPONSE =================


def thinking(chat_id):

    send(chat_id, phrase(THINKING))

    time.sleep(random.uniform(0.4, 0.7))


# ================= MENU =================


def show_menu(chat_id):

    buttons = [
        ["📂 Каталог", "🍳 Что приготовить"],
        ["➕ Добавить продукт"]
    ]

    send(chat_id, "Я на кухне. Что смотрим?", reply_keyboard(buttons))


# ================= CATEGORIES =================


def show_categories(chat_id, data):

    categories = get_categories(data)

    buttons = []
    row = []

    for name, emoji in categories.items():

        row.append(f"{emoji} {name}")

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append(["⬅ Меню"])

    send(chat_id, "Выбирай категорию 👇", reply_keyboard(buttons))


# ================= TYPES =================


def show_types(chat_id, data, category):

    types = get_types(data, category)

    buttons = []
    row = []

    for name, emoji in types.items():

        row.append(f"{emoji} {name}")

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append(["⬅ Категории"])

    send(chat_id, category, reply_keyboard(buttons))


# ================= PRODUCTS =================


def show_products(chat_id, data, category, type_name):

    products = get_products(data, category, type_name)

    buttons = []
    row = []

    for r in products:

        row.append(r[5])

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    buttons.append(["⬅ Типы"])

    send(chat_id, phrase(FOUND), reply_keyboard(buttons))


# ================= PRODUCT CARD =================


def show_product(chat_id, row):

    name = row[5]
    taste = row[6]

    emoji = emoji_for_product(name)
    taste_emoji = extract_taste_emojis(taste)

    stock = get_product(name)

    status = "нет данных"
    price = ""

    if stock:

        if stock.get("status"):
            status = stock["status"]

        if stock.get("price"):
            price = f"{stock['price']} лв"

    text = f"""
{emoji} {format_product_name(name)}

Вкус: {taste}
{taste_emoji}

Дома: {status}
Цена: {price}
"""

    buttons = [

        [{"text": "🍳 Рецепты", "callback_data": f"REC:{name}"}],

        [
            {"text": "✅ Есть", "callback_data": f"STOCK:{name}:есть"},
            {"text": "⚠ Заканчивается", "callback_data": f"STOCK:{name}:мало"}
        ],

        [{"text": "🛒 Купить", "callback_data": f"STOCK:{name}:купить"}]

    ]

    send(chat_id, text, inline_keyboard(buttons))


# ================= COOK ASSISTANT =================


def cook_assistant(chat_id):

    thinking(chat_id)

    stock = get_all()

    available = [
        name for name, data in stock.items()
        if data.get("status") == "есть"
    ]

    if not available:

        send(chat_id, "На кухне пусто 😅")
        return

    ingredient = random.choice(available)

    recipes = recipes_by_ingredient(ingredient)

    if not recipes:

        send(chat_id, phrase(NOT_FOUND))
        return

    send(chat_id, phrase(COOK))

    for r in recipes[:5]:

        send(chat_id, r["strMeal"])


# ================= CALLBACK =================


def handle_callback(update):

    data_cb = update["callback_query"]["data"]

    chat_id = update["callback_query"]["message"]["chat"]["id"]

    if data_cb.startswith("REC:"):

        ingredient = data_cb.split(":")[1]

        thinking(chat_id)

        recipes = recipes_by_ingredient(ingredient)

        if not recipes:

            send(chat_id, phrase(NOT_FOUND))
            return

        for r in recipes[:5]:

            send(chat_id, r["strMeal"])

    if data_cb.startswith("STOCK:"):

        _, name, status = data_cb.split(":")

        set_product(name, status=status)

        send(chat_id, phrase(ACTION))


# ================= MESSAGE =================


def handle_message(update):

    message = update["message"]

    chat_id = message["chat"]["id"]

    text = message.get("text", "").strip()

    data = load_data()

    if text == "/start":

        show_menu(chat_id)
        return

    if text == "📂 Каталог":

        thinking(chat_id)

        show_categories(chat_id, data)
        return

    if text == "🍳 Что приготовить":

        cook_assistant(chat_id)
        return

    if text.startswith("⬅"):

        show_menu(chat_id)
        return

    clean = text.split(" ", 1)[-1]

    categories = get_categories(data)

    if clean in categories:

        thinking(chat_id)

        user_state[chat_id] = {"category": clean}

        show_types(chat_id, data, clean)
        return

    if chat_id in user_state and "category" in user_state[chat_id]:

        category = user_state[chat_id]["category"]

        types = get_types(data, category)

        if clean in types:

            thinking(chat_id)

            user_state[chat_id]["type"] = clean

            show_products(chat_id, data, category, clean)
            return

    if chat_id in user_state and "type" in user_state[chat_id]:

        category = user_state[chat_id]["category"]
        type_name = user_state[chat_id]["type"]

        products = get_products(data, category, type_name)

        for r in products:

            if r[5].lower() == text.lower():

                thinking(chat_id)

                show_product(chat_id, r)
                return

    ingredients = extract_ingredients(text)

    if ingredients:

        for ing in ingredients:

            set_product(ing, status="есть")

        send(chat_id, phrase(ACTION))
        return


# ================= WEBHOOK =================


@app.route("/", methods=["POST"])
def webhook():

    update = request.json

    if "callback_query" in update:
        handle_callback(update)

    if "message" in update:
        handle_message(update)

    return "ok"

if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True)