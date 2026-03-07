import requests
from flask import Flask, request

from config import TOKEN
from data import load_data
from catalog import get_categories, get_types, get_products, paginate, total_pages
from search import search_products
from translations import format_product_name, add_translation
from utils import emoji_for_product, extract_taste_emojis
from admin import update_taste, add_product


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


def reply_keyboard(buttons):

    return {
        "keyboard": buttons,
        "resize_keyboard": True
    }


def inline_keyboard(buttons):

    return {
        "inline_keyboard": buttons
    }


# ================= MENU =================

def show_menu(chat_id):

    user_state[chat_id] = {"level": "menu"}

    buttons = [
        ["📂 Разделы"],
        ["➕ Добавить продукт"]
    ]

    send(
        chat_id,
        "Я на месте. Что смотрим? 👀",
        reply_keyboard(buttons)
    )


# ================= CATEGORIES =================

def show_categories(chat_id, data):

    user_state[chat_id] = {"level": "categories"}

    categories = get_categories(data)

    items = list(categories.items())

    buttons = []

    for i in range(0, len(items), 2):

        pair = items[i:i+2]

        buttons.append([f"{emoji} {name}" for name, emoji in pair])

    buttons.append(["⬅ Назад"])

    send(
        chat_id,
        "Давай определимся с направлением 👇",
        reply_keyboard(buttons)
    )


# ================= TYPES =================

def show_types(chat_id, data, category):

    user_state[chat_id] = {
        "level": "types",
        "category": category
    }

    types = get_types(data, category)

    items = list(types.items())

    buttons = []

    for i in range(0, len(items), 2):

        pair = items[i:i+2]

        buttons.append([f"{emoji} {name}" for name, emoji in pair])

    buttons.append(["⬅ Назад"])

    send(
        chat_id,
        f"Смотрим {category} 👇",
        reply_keyboard(buttons)
    )


# ================= PRODUCTS =================

def show_products(chat_id, data, category, type_name, page=0, message_id=None):

    products = get_products(data, category, type_name)

    user_state[chat_id] = {
        "level": "products",
        "category": category,
        "type": type_name,
        "page": page
    }

    paged = paginate(products, page)

    total = total_pages(products)

    buttons = []

    for row in paged:

        name = format_product_name(row[5])

        emoji = emoji_for_product(row[5], row[4])

        buttons.append([{
            "text": f"{emoji} {name}",
            "callback_data": f"P:{row[0]}"
        }])

    nav = []

    if page > 0:
        nav.append({"text": "⬅", "callback_data": "PAGE:-1"})

    nav.append({"text": f"{page+1}/{total}", "callback_data": "IGNORE"})

    if page < total - 1:
        nav.append({"text": "➡", "callback_data": "PAGE:1"})

    buttons.append(nav)

    if message_id:
        edit(chat_id, message_id, "Смотрим 👇", inline_keyboard(buttons))
    else:
        send(chat_id, "Смотрим 👇", inline_keyboard(buttons))


# ================= WEBHOOK =================

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():

    update = request.json

    data = load_data()

    # ---------- MESSAGE ----------

    if "message" in update:

        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").strip()

        state = user_state.get(chat_id)

        if text == "/start":

            show_menu(chat_id)
            return "ok"

        if text == "📂 Разделы":

            show_categories(chat_id, data)
            return "ok"

        if text == "⬅ Назад":

            if not state:
                show_menu(chat_id)
                return "ok"

            if state["level"] == "categories":
                show_menu(chat_id)

            elif state["level"] == "types":
                show_categories(chat_id, data)

            elif state["level"] == "products":
                show_types(chat_id, data, state["category"])

            return "ok"

        # ===== ADD PRODUCT START =====

        if text == "➕ Добавить продукт":

            user_state[chat_id] = {"level": "add_category"}

            send(chat_id, "В какую категорию добавить продукт?")

            return "ok"

        if state and state.get("level") == "add_category":

            state["category"] = text
            state["level"] = "add_category_emoji"

            send(chat_id, "Эмодзи категории?")
            return "ok"

        if state and state.get("level") == "add_category_emoji":

            state["category_emoji"] = text
            state["level"] = "add_type"

            send(chat_id, "Тип продукта?")
            return "ok"

        if state and state.get("level") == "add_type":

            state["type"] = text
            state["level"] = "add_type_emoji"

            send(chat_id, "Эмодзи типа?")
            return "ok"

        if state and state.get("level") == "add_type_emoji":

            state["type_emoji"] = text
            state["level"] = "add_product"

            send(chat_id, "Название продукта?")
            return "ok"

        if state and state.get("level") == "add_product":

            state["product"] = text
            state["level"] = "add_taste"

            send(chat_id, "Описание вкуса?")
            return "ok"

        if state and state.get("level") == "add_taste":

            add_product(
                state["category"],
                state["category_emoji"],
                state["type"],
                state["type_emoji"],
                state["product"],
                text
            )

            send(chat_id, "Продукт добавлен ✨")

            show_menu(chat_id)
            return "ok"

        # ===== EDIT TASTE =====

        if state and state.get("level") == "edit_taste":

            update_taste(state["row"], text)

            send(chat_id, "Вкус обновлён ✨")

            show_menu(chat_id)

            return "ok"

        # ===== ADD TRANSLATION =====

        if state and state.get("level") == "add_translation":

            add_translation(state["product"], text)

            send(chat_id, "Перевод сохранён 🇧🇬")

            show_menu(chat_id)

            return "ok"

        # ===== CATEGORY CLICK =====

        clean = text.split(" ", 1)[-1]

        categories = get_categories(data)

        if clean in categories:

            show_types(chat_id, data, clean)
            return "ok"

        # ===== TYPE CLICK =====

        if state and state.get("level") == "types":

            types = get_types(data, state["category"])

            if clean in types:

                show_products(chat_id, data, state["category"], clean, 0)
                return "ok"

        # ===== SEARCH =====

        results = search_products(text, data)

        if results:

            buttons = []

            for row in results:

                name = format_product_name(row[5])
                emoji = emoji_for_product(row[5], row[4])

                buttons.append([{
                    "text": f"{emoji} {name}",
                    "callback_data": f"P:{row[0]}"
                }])

            send(
                chat_id,
                "Нашёл кое-что 👀",
                inline_keyboard(buttons)
            )

            return "ok"

    # ---------- CALLBACK ----------

    if "callback_query" in update:

        callback = update["callback_query"]

        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        data_cb = callback["data"]

        state = user_state.get(chat_id)

        if data_cb == "IGNORE":
            return "ok"

        if data_cb.startswith("P:"):

            row_id = int(data_cb.split(":")[1])

            for row in data:

                if row[0] == row_id:
                    product = row
                    break

            name = format_product_name(product[5])

            emoji = emoji_for_product(product[5], product[4])

            taste = extract_taste_emojis(product[6])

            text = (
                f"{emoji} {name}\n\n"
                f"{product[6]}\n\n"
                f"{taste}"
            )

            buttons = [[
                {"text": "⬅ К списку", "callback_data": "BACK"},
                {"text": "✏ Изменить вкус", "callback_data": f"EDIT:{row_id}"},
                {"text": "🇧🇬 Перевод", "callback_data": f"TR:{product[5]}"}
            ]]

            edit(chat_id, message_id, text, inline_keyboard(buttons))

            return "ok"

        if data_cb == "BACK":

            show_products(
                chat_id,
                data,
                state["category"],
                state["type"],
                state["page"],
                message_id
            )

            return "ok"

        if data_cb.startswith("PAGE:"):

            delta = int(data_cb.split(":")[1])

            show_products(
                chat_id,
                data,
                state["category"],
                state["type"],
                state["page"] + delta,
                message_id
            )

            return "ok"

        if data_cb.startswith("EDIT:"):

            row = int(data_cb.split(":")[1])

            user_state[chat_id] = {
                "level": "edit_taste",
                "row": row
            }

            send(chat_id, "Напиши новый вкус 👀")

            return "ok"

        if data_cb.startswith("TR:"):

            product = data_cb.split(":", 1)[1]

            user_state[chat_id] = {
                "level": "add_translation",
                "product": product
            }

            send(chat_id, f"Напиши перевод для:\n{product}")

            return "ok"

    return "ok"


@app.route("/")
def home():
    return "Bot is running"


if __name__ == "__main__":

    import os

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)