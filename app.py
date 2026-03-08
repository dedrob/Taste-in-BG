import requests
from flask import Flask, request

from config import TOKEN
from data import load_data
from catalog import paginate, total_pages
from search import search_products
from translations import format_product_name, add_translation
from utils import emoji_for_product, extract_taste_emojis
from admin import update_taste, add_product
from recipes import recipes_by_ingredient, get_recipe
from stock import get_product, set_product, load_stock
from speech_db import phrase
from nlp_food import extract_ingredients
import time


app = Flask(__name__)

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"

user_state = {}
memory = {}

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


def inline_keyboard(buttons):
    return {"inline_keyboard": buttons}

# ================= ЖИВОЙ ОТВЕТ =================

def human_reply(chat_id, thinking_group, answer, keyboard=None):

    # первое сообщение — как будто бот думает
    send(chat_id, phrase(thinking_group))

    time.sleep(0.5)

    # второе сообщение — основной ответ
    send(chat_id, answer, keyboard)

# ================= Меню =================

def show_menu(chat_id):

    buttons = [
        [{"text": "📂 Каталог", "callback_data": "MENU:CAT"}],
        [{"text": "🍳 Что можно приготовить", "callback_data": "COOK"}],
        [{"text": "➕ Добавить продукт", "callback_data": "MENU:ADD"}],
    ]   

    human_reply(
        chat_id,
        "reaction",
        "Я на месте. Что смотрим? 👀",
        inline_keyboard(buttons)
)

# ================= CATEGORIES =================

def show_categories(chat_id, data):

    categories = {}

    for row in data:

        category = row[1].strip()
        emoji = row[2].strip()

        if category not in categories:
            categories[category] = emoji

    buttons = []

    for name, emoji in categories.items():

        buttons.append([{"text": f"{emoji} {name}", "callback_data": f"CAT:{name}"}])

    buttons.append([{"text": "⬅ Меню", "callback_data": "MENU"}])

    send(chat_id, "Выбирай раздел 👇", inline_keyboard(buttons))


# ================= TYPES =================
def show_types(chat_id, data, category):

    types = {}

    for row in data:

        if row[1] != category:
            continue

        t = row[3]
        emoji = row[4]

        if t not in types:
            types[t] = emoji

    buttons = []

    for name, emoji in types.items():

        buttons.append(
            [{"text": f"{emoji} {name}", "callback_data": f"TYPE:{category}:{name}"}]
        )

    buttons.append([{"text": "⬅ Категории", "callback_data": "MENU:CAT"}])

    send(chat_id, category, inline_keyboard(buttons))


# ================= PRODUCTS =================
def show_products(chat_id, data, category, type_name, page=0, message_id=None):

    products = []

    for row in data:

        if row[1] == category and row[3] == type_name:
            products.append(row)

    paged = paginate(products, page)
    total = total_pages(products)

    user_state[chat_id] = {"category": category, "type": type_name, "page": page}

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

    buttons.append([{"text": "⬅ Типы", "callback_data": f"CAT:{category}"}])

    if message_id:
        edit(chat_id, message_id, "Список продуктов 👇", inline_keyboard(buttons))
    else:
        send(chat_id, "Список продуктов 👇", inline_keyboard(buttons))


# ================= ИНФОРМАЦИЯ О ПРОДУКТЕ ДОМА =================

def product_stock_info(product_name):

    data = get_product(product_name)

    if not data:
        return "❌ нет данных", "—"

    status = data.get("status")
    price = data.get("price")

    status_map = {
        "есть": "✅ есть",
        "заканчивается": "⚠ заканчивается",
        "купить": "❌ нужно купить"
    }

    status_text = status_map.get(status, "❌ нет данных")

    if price:
        price_text = f"{price} лв"
    else:
        price_text = "—"

    return status_text, price_text


# ================= КАРТОЧКА ПРОДУКТА =================

def show_product(chat_id, message_id, data, row_id):

    product = None

    for row in data:
        if row[0] == row_id:
            product = row
            break

    if not product:
        edit(chat_id, message_id, "Продукт не найден")
        return

    name = format_product_name(product[5])
    emoji = emoji_for_product(product[5])
    taste = product[6]

    taste_emojis = extract_taste_emojis(taste)

    status_text, price_text = product_stock_info(product[5])

    text = (
        f"{emoji} {name}\n\n"
        f"{taste}\n\n"
        f"{taste_emojis}\n\n"
        f"📦 дома: {status_text}\n"
        f"💰 цена: {price_text}"
    )

    buttons = [
        [
            {"text": "🍳 Рецепты", "callback_data": f"REC:{product[5]}"},
            {"text": "✏ Вкус", "callback_data": f"EDIT:{row_id}"}
        ],
        [
            {"text": "📦 есть", "callback_data": f"STOCK:{product[5]}:есть"},
            {"text": "⚠ заканчивается", "callback_data": f"STOCK:{product[5]}:заканчивается"}
        ],
        [
            {"text": "❌ купить", "callback_data": f"STOCK:{product[5]}:купить"}
        ],
        [
            {"text": "🇧🇬 Перевод", "callback_data": f"TR:{product[5]}"}
        ],
        [
            {"text": "⬅ Назад", "callback_data": "BACK"}
        ]
    ]

    if message_id:
        edit(chat_id, message_id, text, inline_keyboard(buttons))
    else:
        send(chat_id, text, inline_keyboard(buttons))


# ================= ИНГРЕДИЕНТЫ РЕЦЕПТА =================

def recipe_ingredients(recipe):

    ingredients = []

    for i in range(1, 21):

        ing = recipe.get(f"strIngredient{i}")

        if ing and ing.strip():
            ingredients.append(ing.lower())

    return ingredients


# ================= ПРОВЕРКА ИНГРЕДИЕНТОВ =================

def check_ingredients(ingredients):

    result = []

    for ing in ingredients:

        data = get_product(ing)

        if not data:
            result.append(f"❌ {ing}")
            continue

        status = data.get("status")

        if status == "есть":
            result.append(f"✅ {ing}")

        elif status == "заканчивается":
            result.append(f"⚠ {ing}")

        else:
            result.append(f"❌ {ing}")

    return "\n".join(result)

# ================= РЕЦЕПТЫ ИЗ ПРОДУКТОВ ДОМА =================

def recipes_from_home():

    products = []
    stock_data = load_stock()

    if not stock_data:
        return []

    for name, info in stock_data.items():
        if info.get("status") == "есть":
            products.append(name)

    results = {}
    
    for p in products:

        recipes = recipes_by_ingredient(p)

        for r in recipes:
            results[r["idMeal"]] = r

    return list(results.values())[:10]

# ================= WEBHOOK =================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():

    update = request.json
    data = load_data()

    # ================= CALLBACK =================

    if "callback_query" in update:

        callback = update["callback_query"]

        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        data_cb = callback["data"]

        state = user_state.get(chat_id)

        # -------- добавление перевода --------
        
        if data_cb.startswith("TR:"):

            name = data_cb.split(":",1)[1]

            user_state[chat_id] = {
                "mode": "add_translation",
                "product": name
    }

            send(chat_id, "Напиши перевод продукта")

            return "ok"
        

# -------- изменение статуса продукта --------

        if data_cb.startswith("STOCK:"):

            _, name, status = data_cb.split(":")

            set_product(name, status=status)

            for row in data:
                if row[5] == name:
                    show_product(chat_id, message_id, data, row[0])
                    break
                
            return "ok"
        
        # -------- меню --------

        if data_cb == "MENU":
            show_menu(chat_id)
            return "ok"

        if data_cb == "MENU:CAT":
            show_categories(chat_id, data)
            return "ok"

        # -------- категории --------

        if data_cb.startswith("CAT:"):

            category = data_cb.split(":", 1)[1]

            show_types(chat_id, data, category)

            return "ok"

        # -------- тип продукта --------

        if data_cb.startswith("TYPE:"):

            _, category, type_name = data_cb.split(":")

            show_products(chat_id, data, category, type_name)

            return "ok"

        # -------- карточка продукта --------

        if data_cb.startswith("P:"):

            row_id = int(data_cb.split(":")[1])

            show_product(chat_id, message_id, data, row_id)

            return "ok"

        # -------- добавить категорию --------
        if data_cb == "MENU:ADD":

            user_state[chat_id] = {"mode": "add_category"}

            send(chat_id, "Категория продукта?")

            return "ok"
        
        if data_cb.startswith("EDIT:"):

            row_id = int(data_cb.split(":")[1])

            user_state[chat_id] = {
                "mode": "edit_taste",
                "row": row_id
    }

            send(chat_id, "Напиши новый вкус продукта")

            return "ok"

        # -------- назад --------

        if data_cb == "BACK":

            if state:

                show_products(
                    chat_id,
                    data,
                    state["category"],
                    state["type"],
                    state["page"],
                    message_id,
                )

            return "ok"

        # -------- страницы --------

        if data_cb.startswith("PAGE:"):

            delta = int(data_cb.split(":")[1])

            show_products(
                chat_id,
                data,
                state["category"],
                state["type"],
                state["page"] + delta,
                message_id,
            )

            return "ok"

        # -------- рецепты --------

        if data_cb.startswith("REC:"):

            ingredient = data_cb.split(":", 1)[1]

            recipes = recipes_by_ingredient(ingredient)

            buttons = []

            for r in recipes:

                buttons.append(
                    [{"text": r["strMeal"], "callback_data": f"RECIPE:{r['idMeal']}"}]
                )

            human_reply(
                chat_id,
                "thinking",
                "Сейчас гляну что можно приготовить 👇",
                inline_keyboard(buttons)
            )

            return "ok"

        # -------- открыть рецепт --------
        if data_cb.startswith("RECIPE:"):

            recipe_id = data_cb.split(":")[1]

            recipe = get_recipe(recipe_id)

            if not recipe:
                edit(chat_id, message_id, "Не удалось загрузить рецепт")
                return "ok"

            ingredients = recipe_ingredients(recipe)

            status = check_ingredients(ingredients)

            instructions = recipe.get("strInstructions", "")

            text = (
                f"🍳 {recipe.get('strMeal','')}\n\n"
                f"ИНГРЕДИЕНТЫ:\n\n"
                f"{status}\n\n"
                f"РЕЦЕПТ:\n\n"
                f"{instructions[:800]}..."
    )

            edit(chat_id, message_id, text)

            return "ok"

    # ================= MESSAGE =================

    if "message" in update:

        chat_id = update["message"]["chat"]["id"]
        text = update["message"].get("text", "").lower()

        # --- старт ---
        if text == "/start":
            show_menu(chat_id)
            return "ok"

# --- анализ ингредиентов ---
    ingredients = extract_ingredients(text)
    
    if ingredients:
        memory[chat_id] = ingredients
    results = {}

    if ingredients:

        for ing in ingredients:

            recipes = recipes_by_ingredient(ing)

            for r in recipes:
                results[r["idMeal"]] = r

    buttons = []

    for r in results.values():

        buttons.append([{
            "text": r["strMeal"],
            "callback_data": f"RECIPE:{r['idMeal']}"
        }])

        if buttons:

            human_reply(
                chat_id,
                "thinking",
                "Сейчас гляну что можно приготовить 👇",
                inline_keyboard(buttons)
            )

            return "ok"

        # --- поиск продукта ---
        results = search_products(text, data)

        if results:

            buttons = []

            for row in results:

                name = format_product_name(row[5])
                emoji = emoji_for_product(row[5])

                buttons.append([{
                    "text": f"{emoji} {name}",
                    "callback_data": f"P:{row[0]}"
                }])

            human_reply(
                chat_id,
                "thinking",
                "Вот что я нашёл 👇",
                inline_keyboard(buttons)
            )

            return "ok"

        send(chat_id, phrase("reaction"))

        return "ok"

@app.route("/")
def home():
    return "Bot is running"


if __name__ == "__main__":

    import os

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)
