import requests
import random
import time

from stock import set_product, get_product, get_all
from flask import Flask, request

from config import TOKEN
from data import load_data
from catalog import get_categories, get_types, get_products, paginate, total_pages
from search import search_products
from translations import format_product_name, add_translation
from utils import emoji_for_product, extract_taste_emojis
from admin import update_taste, add_product
from recipes import recipes_by_ingredient, get_recipe
from nlp_food import extract_ingredients
from speech_db import phrase

def human_pause(a=0.4, b=1.2):

    time.sleep(random.uniform(a, b))


def typing(chat_id):

    requests.post(
        f"{TELEGRAM_URL}/sendChatAction",
        json={
            "chat_id": chat_id,
            "action": "typing"
        }
    )


def maybe_reaction(chat_id):

    if random.random() < 0.35:

        send(chat_id, phrase("reaction"))
        human_pause()


app = Flask(__name__)

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"

user_state = {}


# ================= TELEGRAM =================


def send(chat_id, text, keyboard=None):

    payload = {"chat_id": chat_id, "text": text}

    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(f"{TELEGRAM_URL}/sendMessage", json=payload)


def edit(chat_id, message_id, text, keyboard=None):

    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}

    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(f"{TELEGRAM_URL}/editMessageText", json=payload)


def reply_keyboard(buttons):

    return {"keyboard": buttons, "resize_keyboard": True}


def inline_keyboard(buttons):

    return {"inline_keyboard": buttons}


# ================= MENU =================


def show_menu(chat_id):

    user_state[chat_id] = {"level": "menu"}

    buttons = [
        ["📂 Разделы"],
        ["🛒 Список покупок"],
        ["🍳 Что приготовить"],
        ["➕ Добавить продукт"],
    ]

    send(chat_id, "Я на месте. Что смотрим? 👀", reply_keyboard(buttons))


# ================= CATEGORIES =================


def show_categories(chat_id, data):

    user_state[chat_id] = {"level": "categories"}

    categories = get_categories(data)

    items = list(categories.items())

    buttons = []

    for i in range(0, len(items), 2):

        pair = items[i : i + 2]

        buttons.append([f"{emoji} {name}" for name, emoji in pair])

    buttons.append(["⬅ Назад"])

    send(chat_id, "Давай определимся с направлением 👇", reply_keyboard(buttons))


# ================= TYPES =================


def show_types(chat_id, data, category):

    user_state[chat_id] = {"level": "types", "category": category}

    types = get_types(data, category)

    items = list(types.items())

    buttons = []

    for i in range(0, len(items), 2):

        pair = items[i : i + 2]

        buttons.append([f"{emoji} {name}" for name, emoji in pair])

    buttons.append(["⬅ Назад"])

    send(chat_id, f"Смотрим {category} 👇", reply_keyboard(buttons))


# ================= PRODUCTS =================


def show_products(chat_id, data, category, type_name, page=0, message_id=None):

    products = get_products(data, category, type_name)

    user_state[chat_id] = {
        "level": "products",
        "category": category,
        "type": type_name,
        "page": page,
    }

    paged = paginate(products, page)

    total = total_pages(products)

    buttons = []

    for row in paged:

        name = format_product_name(row[5])
        emoji = emoji_for_product(row[5], row[4])

        buttons.append([{"text": f"{emoji} {name}", "callback_data": f"P:{row[0]}"}])

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

    if "message" in update:

        message = update["message"]
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        typing(chat_id)
        human_pause()


        state = user_state.get(chat_id)

        if state and state.get("level") == "set_price":

            name = state["product"]

            try:
                price = float(text.replace(",", "."))

            except:
                send(chat_id, "Напиши цену числом")
                return "ok"

            set_product(name, price=price)

            send(chat_id, f"Цена для {name}: {price} лв")

            show_menu(chat_id)

            return "ok"

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

        if text == "➕ Добавить продукт":

            user_state[chat_id] = {"level": "add_category"}

            categories = get_categories(data)

            buttons = []

            for name, emoji in categories.items():
                buttons.append([f"{emoji} {name}"])

            buttons.append(["⬅ Назад"])

            send(
                chat_id,
                "В какую категорию добавить продукт? Можно выбрать или написать новую 👇",
                reply_keyboard(buttons),
            )

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
                text,
            )

            send(chat_id, "Продукт добавлен ✨")
            show_menu(chat_id)
            return "ok"

        results = search_products(text, data)

        if results:

            buttons = []

            for row in results:

                name = format_product_name(row[5])
                emoji = emoji_for_product(row[5], row[4])

                buttons.append(
                    [{"text": f"{emoji} {name}", "callback_data": f"P:{row[0]}"}]
                )

            send(chat_id, "Нашёл кое-что 👀", inline_keyboard(buttons))
            return "ok"

        if text == "🛒 Список покупок":

            data = get_all()

            items = []

            for name, info in data.items():

                if (
                    info.get("status") == "купить"
                    or info.get("status") == "заканчивается"
                ):
                    items.append(name)

            if not items:

                send(chat_id, "🛒 Покупать пока ничего не нужно")

    else:

        text_out = "🛒 Нужно купить:\n\n"

        for i in items:
            text_out += f"• {i}\n"

        send(chat_id, text_out)

        return "ok"

    if text == "🍳 Что приготовить":

        stock = get_all()

        ingredients = []

        for name, info in stock.items():

            if info.get("status") == "есть":
                ingredients.append(name)

        if not ingredients:

            send(chat_id, "Пока нет продуктов со статусом 'есть'")
            return "ok"

        buttons = []

        found = []

        for ingredient in ingredients:

            recipes = recipes_by_ingredient(ingredient)

            for r in recipes:

                if r["idMeal"] not in found:

                    found.append(r["idMeal"])

                    buttons.append(
                        [
                            {
                                "text": f"{r['strMeal']} ({ingredient})",
                                "callback_data": f"RECIPE:{r['idMeal']}",
                            }
                        ]
                    )

            if len(buttons) >= 8:
                break

        if not buttons:

            send(chat_id, "Не нашёл рецептов 👀")
            return "ok"

        send(chat_id, "🍳 Можно приготовить:", inline_keyboard(buttons[:8]))

        return "ok"
    
    ingredients = extract_ingredients(text)

    if ingredients:

        send(chat_id, phrase("THINKING"))

        ingredient = ingredients[0]

        recipes = recipes_by_ingredient(ingredient)

        if recipes:

            buttons = []

        for r in recipes:

            buttons.append([
                {"text": r["strMeal"], "callback_data": f"RECIPE:{r['idMeal']}`"}
            ])

        send(
            chat_id,
            phrase("RECIPES"),
            inline_keyboard(buttons)
        )

        return "ok"

    if "callback_query" in update:

        callback = update["callback_query"]

        requests.post(
            f"{TELEGRAM_URL}/answerCallbackQuery",
            json={"callback_query_id": callback["id"]},
        )

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

            text = f"{phrase('open_product')}\n\n{emoji} {name}\n\n{product[6]}\n\n{taste}"

            buttons = [
                [
                    {"text": "💰 Цена", "callback_data": f"PRICE:{product[5]}"},
                    {"text": "📦 Наличие", "callback_data": f"STOCK:{product[5]}"},
                ],
                [{"text": "🍳 Рецепты", "callback_data": f"REC:{product[5]}"}],
            ]

            edit(chat_id, message_id, text, inline_keyboard(buttons))
            return "ok"

        if data_cb.startswith("REC:"):

            ingredient = data_cb.split(":")[1]
            recipes = recipes_by_ingredient(ingredient)

            if not recipes:
                send(chat_id, "Пока не нашёл рецептов 👀")
                return "ok"

            buttons = []

            for r in recipes:

                buttons.append(
                    [{"text": r["strMeal"], "callback_data": f"RECIPE:{r['idMeal']}"}]
                )

            edit(
                chat_id,
                message_id,
                phrase("recipes"),
                inline_keyboard(buttons),
            )
            return "ok"

        if data_cb.startswith("RECIPE:"):

            recipe_id = data_cb.split(":")[1]
            recipe = get_recipe(recipe_id)

            text = f"🍳 {recipe['strMeal']}\n\n{recipe['strInstructions'][:800]}..."

            edit(chat_id, message_id, text)
            return "ok"

        if data_cb.startswith("HAVE:"):

            name = data_cb.split(":")[1]

            set_product(name, status="есть")

            send(chat_id, phrase("have", name=name))
            return "ok"

        if data_cb.startswith("LOW:"):

            name = data_cb.split(":")[1]

            set_product(name, status="заканчивается")

            send(chat_id, phrase("low", name=name))
            return "ok"

        if data_cb.startswith("BUY:"):

            name = data_cb.split(":")[1]

            set_product(name, status="купить")

            send(chat_id, phrase("buy", name=name))

            return "ok"


        if data_cb.startswith("STOCK:"):

            name = data_cb.split(":")[1]

            buttons = [
                [{"text": "📦 Есть", "callback_data": f"HAVE:{name}"}],
                [{"text": "⚠ Заканчивается", "callback_data": f"LOW:{name}"}],
                [{"text": "🛒 Купить", "callback_data": f"BUY:{name}"}],
                [{"text": "❌ Нет", "callback_data": f"NONE:{name}"}],
            ]

            edit(
                chat_id,
                message_id,
                f"Наличие продукта: {name}",
                inline_keyboard(buttons),
            )

    return "ok"

@app.route("/")
def home():
    return "Bot is running"


if __name__ == "__main__":

    import os

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)
