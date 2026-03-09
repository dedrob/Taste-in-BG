import os
import requests
import time
import random

from flask import Flask, request

from config import TOKEN
from data import load_data
from catalog import get_categories, get_types, get_products
from recipes import recipes_by_ingredient, get_recipe
from stock import get_product, set_product, get_all
from translations import format_product_name, add_translation
from utils import emoji_for_product, extract_taste_emojis
from nlp_food import extract_ingredients
from search import search_products
from deep_translator import GoogleTranslator

from phrases import THINKING, FOUND, NOT_FOUND, ACTION, COOK, phrase


app = Flask(__name__)

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"

user_state = {}

# ================= Логи =================

logs = []

# ==========================================
# Добавляет событие в список логов.
# Используется для отладки: сообщения, кнопки, ошибки.
# Хранит только последние 100 записей.
# ==========================================
def log_event(event):

    logs.append(event)

    # ограничим размер
    if len(logs) > 100:
        logs.pop(0)

# ================= TELEGRAM =================
# ==========================================
# Отправляет сообщение пользователю в Telegram.
# chat_id — ID пользователя
# text — текст сообщения
# keyboard — клавиатура (если нужно показать кнопки)
# ==========================================
def send(chat_id, text, keyboard=None):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    requests.post(f"{TELEGRAM_URL}/sendMessage", json=payload)


# ==========================================
# Отправляет пользователю фото с подписью
# Используется для рецептов блюд
# ==========================================
def send_photo(chat_id, photo_url, caption=None):

    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "parse_mode": "HTML"
    }

    if caption:
        payload["caption"] = caption

    requests.post(
        f"{TELEGRAM_URL}/sendPhoto",
        json=payload
    )


# ==========================================
# Отправляет сообщение пользователю в Telegram.
# chat_id — ID пользователя
# text — текст сообщения
# keyboard — клавиатура (если нужно показать кнопки)
# ==========================================
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
# ==========================================
# Редактирует уже отправленное сообщение.
# Используется для inline-кнопок.
# ==========================================
def translate_to_ru(text):

    if not text:
        return text

    try:
        return GoogleTranslator(source="auto", target="ru").translate(text)

    except:
        return text

# ==========================================
# Создаёт обычную клавиатуру Telegram
# (кнопки под строкой ввода).
# rows — список строк кнопок.
# ==========================================
def reply_keyboard(rows):

    return {
        "keyboard": rows,
        "resize_keyboard": True
    }

# ==========================================
# Создаёт inline-кнопки (кнопки внутри сообщения).
# Используется для рецептов и карточек продукта.
# ==========================================
def inline_keyboard(rows):

    return {
        "inline_keyboard": rows
    }


# ==========================================
# Создаёт inline-кнопки (кнопки внутри сообщения).
# Используется для рецептов и карточек продукта.
# ==========================================
def thinking(chat_id):

    send(chat_id, phrase(THINKING))

    time.sleep(random.uniform(0.4, 0.7))


# ==========================================
# Бот отправляет случайную фразу «думаю...»
# и делает небольшую паузу.
# Это делает ответы более живыми.
# ==========================================
def show_menu(chat_id):

    buttons = [
        ["📂 Каталог"], 
        ["🍳 Что приготовить"],
        ["➕ Добавить продукт"],
        ["📦 Моя кухня"]
    ]

    send(chat_id, "Я на кухне. Что смотрим?", reply_keyboard(buttons))


# ==========================================
# Показывает главное меню бота.
# Здесь пользователь выбирает:
# каталог, рецепты или добавление продукта.
# ==========================================
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


# ==========================================
# Показывает подкатегории выбранной категории.
# Например: категория "Напитки"
# типы: "Чай", "Кофе".
# ==========================================
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


# ==========================================
# Показывает подкатегории выбранной категории.
# Например: категория "Напитки"
# типы: "Чай", "Кофе".
# ==========================================
def show_products(chat_id, data, category, type_name, page=0):

    products = get_products(data, category, type_name)

    per_page = 6
    start = page * per_page
    end = start + per_page

    items = products[start:end]

    buttons = []
    row = []

    for r in items:

        name = r[5]
        emoji = emoji_for_product(name)

        row.append(f"{emoji} {name}")

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    pages = max(1, (len(products) + per_page - 1) // per_page)

    nav = []

    if page > 0:
        nav.append(f"⬅ PAGE:{page-1}")

    nav.append(f"{page+1}/{pages}")

    if page < pages - 1:
        nav.append(f"PAGE:{page+1} ➡")

    buttons.append(nav)

    buttons.append(["⬅ Типы"])

    send(chat_id, phrase(FOUND), reply_keyboard(buttons))


# ==========================================
# Показывает карточку продукта.
# Отображает:
# - название
# - вкус
# - статус дома
# - цену
# - кнопки действий
# ==========================================
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

    [
        {"text": "🛒 Купить", "callback_data": f"STOCK:{name}:купить"},
        {"text": "💰 Цена", "callback_data": f"PRICE:{name}"}
    ],

    [
        {"text": "🇧🇬 Перевести", "callback_data": f"TR:{name}"}
    ]

]

    send(chat_id, text, inline_keyboard(buttons))

# ==========================================
# Показывает все продукты которые есть дома
# ==========================================
def show_kitchen(chat_id):

    stock = get_all()

    if not stock:

        send(chat_id, "На кухне пока пусто")
        return

    text = "📦 Твои продукты:\n\n"

    for name, data in stock.items():

        emoji = emoji_for_product(name)

        status = data.get("status", "нет данных")
        price = data.get("price")

        status_icon = {
            "есть": "✅",
            "мало": "⚠",
            "купить": "🛒"
        }.get(status, "")

        line = f"{status_icon} {emoji} {name}"

        if price:
            line += f" — {price} лв"

        text += line + "\n"

    send(chat_id, text)


# ==========================================
# Выбирает случайный продукт из кухни
# и ищет рецепты с ним.
# Используется для кнопки "Что приготовить".
# ==========================================
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


# Обрабатывает нажатия inline-кнопок.
def handle_callback(update):

    data_cb = update["callback_query"]["data"]

    chat_id = update["callback_query"]["message"]["chat"]["id"]
    
    log_event({
        "type": "callback",
        "chat_id": chat_id,
        "data": data_cb
    })
    
    # REC: продукт → список рецептов
    if data_cb.startswith("REC:"):

        ingredient = data_cb.split(":")[1]

        thinking(chat_id)

        recipes = recipes_by_ingredient(ingredient)

        if not recipes:

            send(chat_id, phrase(NOT_FOUND))
            return

        buttons = []

        for r in recipes[:5]:

            title = translate_to_ru(r["strMeal"])

            buttons.append([
            {
                "text": title,
                "callback_data": f"RECIPE:{r['idMeal']}"
            }
        ])

        send(chat_id, "Вот рецепты:", inline_keyboard(buttons))

        return
    
# RECIPE: id → открыть рецепт
    if data_cb.startswith("RECIPE:"):

        recipe_id = data_cb.split(":")[1]

        thinking(chat_id)

        recipe = get_recipe(recipe_id)

        if not recipe:

            send(chat_id, "Рецепт не найден")
            return

        title = translate_to_ru(recipe["strMeal"])
        
        instructions = translate_to_ru(recipe["strInstructions"])

        photo = recipe["strMealThumb"]

        text = f"""
    🍳 {title}

    📋 Инструкция:

    {instructions[:1000]}
    """
        # показываем рецепт с фото блюда
        send_photo(chat_id, photo, caption=text)

        return

# STOCK → изменить статус продукта
    if data_cb.startswith("STOCK:"):

        _, name, status = data_cb.split(":")

        set_product(name, status=status)

        send(chat_id, phrase(ACTION))

# TR → добавить перевод
    if data_cb.startswith("TR:"):

        name = data_cb.split(":")[1]

        user_state[chat_id] = {"translate_product": name}

        send(chat_id, "Напиши перевод")

        return
    

# Главная функция обработки сообщений.
# Определяет что написал пользователь:
def handle_message(update):

    message = update["message"]

    chat_id = message["chat"]["id"]

    text = message.get("text", "").strip()
    
     # записываем сообщение в лог
    log_event({
        "type": "message",
        "chat_id": chat_id,
        "text": text
    })

# загружаем таблицу продуктов
    data = load_data()

# ================= ПАГИНАЦИЯ =================
    # пользователь нажал кнопку перехода страницы
    if text.startswith("PAGE:"):

        page = int(text.split(":")[1])

        state = user_state.get(chat_id)

        if state and "category" in state and "type" in state:

            show_products(
                chat_id,
                data,
                state["category"],
                state["type"],
                page
        )

        return
    
    
# ================= СТАРТ =====================
    if text == "/start":

        show_menu(chat_id)
        return
    
    
# ================= КАТАЛОГ ===================  
    if text == "📂 Каталог":

        thinking(chat_id)

        show_categories(chat_id, data)
        return


# ================= ЧТО ПРИГОТОВИТЬ =================
    if text == "🍳 Что приготовить":

        cook_assistant(chat_id)
        return


 # ================= НАЗАД =================
    if text.startswith("⬅"):

        show_menu(chat_id)
        return


# ================= ОПРЕДЕЛЯЕМ КАТЕГОРИЮ =================
    clean = text.split(" ", 1)[-1]

    categories = get_categories(data)

    if clean in categories:

        thinking(chat_id)

        user_state[chat_id] = {"category": clean}

        show_types(chat_id, data, clean)
        return


# ================= ОПРЕДЕЛЯЕМ ТИП =================
    if chat_id in user_state and "category" in user_state[chat_id]:

        category = user_state[chat_id]["category"]

        types = get_types(data, category)

        if clean in types:

            thinking(chat_id)

            user_state[chat_id]["type"] = clean

            show_products(chat_id, data, category, clean)
            return


 # ================= ОТКРЫВАЕМ ПРОДУКТ =================
    if chat_id in user_state and "type" in user_state[chat_id]:

        category = user_state[chat_id]["category"]
        type_name = user_state[chat_id]["type"]

        products = get_products(data, category, type_name)

        clean_text = text.split("/")[0].strip()
        clean_text = clean_text.split(" ", 1)[-1]

        for r in products:

            if r[5].lower() == text.lower():

                thinking(chat_id)

                show_product(chat_id, r)
                return
 
 
 # ================= ПЕРЕВОД ПРОДУКТА =================
    # Если пользователь нажал кнопку "🇧🇬 Перевести",
    # бот ожидает ввод перевода.
    # Здесь мы сохраняем перевод продукта.  
    if chat_id in user_state and "translate_product" in user_state[chat_id]:

        product = user_state[chat_id]["translate_product"]

        add_translation(product, text)

        send(chat_id, f"Сохранил перевод:\n{product} / {text}")

        user_state.pop(chat_id)

        return        
    
    
 # ================= ПОИСК ПРОДУКТА =================
# Если пользователь просто написал текст,
# пробуем найти продукты в каталоге.   
    results = search_products(text, data)
    if results:

        thinking(chat_id)

        buttons = []
        row = []

        for r in results[:10]:

            name = r[5]
            emoji = emoji_for_product(name)

            row.append(f"{emoji} {name}")

            if len(row) == 2:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        buttons.append(["⬅ Меню"])

        send(chat_id, "Вот что нашёл", reply_keyboard(buttons))
        return


# ================= ДОБАВЛЕНИЕ ПРОДУКТОВ В КУХНЮ =================
    # Если пользователь написал что-то вроде:
    # "у меня есть бекон яйца"
    # бот извлекает ингредиенты и добавляет их в stock.json.
    ingredients = extract_ingredients(text)
    if ingredients:

        for ing in ingredients:

            set_product(ing, status="есть")

        send(chat_id, phrase(ACTION))
        return

# ================= МОЯ КУХНЯ =================
# показывает продукты которые есть дома
    if text == "📦 Моя кухня":

        thinking(chat_id)

        show_kitchen(chat_id)

        return

# ==========================================
# Главная точка входа Telegram webhook.
# Принимает обновления от Telegram
# и передаёт их нужным обработчикам.
# ==========================================
@app.route("/", methods=["GET", "POST"])
def webhook():

    if request.method == "GET":
        return "Bot is running"

    update = request.json

    if "message" in update:
        handle_message(update)

    if "callback_query" in update:
        handle_callback(update)

    return "ok"


# ==========================================
# Проверяет здоровье бота:
# - сервер
# - Google Sheets
# - API рецептов
# - stock.json
# Используется для диагностики.
# ==========================================
@app.route("/health", methods=["GET"])
def health():

    status = {
        "server": "ok",
        "google_sheets": "unknown",
        "recipes_api": "unknown",
        "stock": "unknown",
        "products_loaded": 0
    }

    # Проверка Google Sheets
    try:
        data = load_data()
        status["google_sheets"] = "ok"
        status["products_loaded"] = len(data)
    except Exception as e:
        status["google_sheets"] = f"error: {str(e)}"

    # Проверка рецептов API
    try:
        r = requests.get("https://www.themealdb.com/api/json/v1/1/search.php?s=egg", timeout=5)
        if r.status_code == 200:
            status["recipes_api"] = "ok"
        else:
            status["recipes_api"] = "error"
    except:
        status["recipes_api"] = "offline"

    # Проверка stock.json
    try:
        stock = get_all()
        status["stock"] = f"ok ({len(stock)} items)"
    except Exception as e:
        status["stock"] = f"error: {str(e)}"

    return status


# ==========================================
# Показывает диагностическую информацию:
# - количество продуктов
# - продукты дома
# - состояние пользователя
# ==========================================
@app.route("/debug", methods=["GET"])
def debug():

    info = {}

    try:
        data = load_data()
        info["products_total"] = len(data)
        info["products_sample"] = [row[5] for row in data[:5]]
    except Exception as e:
        info["products_error"] = str(e)

    try:
        stock = get_all()
        info["stock_items"] = list(stock.keys())
        info["stock_total"] = len(stock)
    except Exception as e:
        info["stock_error"] = str(e)

    info["user_state"] = user_state

    text = f"""
📦 Продуктов в каталоге: {info.get("products_total")}

🧾 Пример продуктов:
{info.get("products_sample")}

🥚 Продукты дома:
{info.get("stock_items")}

📊 Всего дома:
{info.get("stock_total")}

👤 Состояние пользователя:
{info.get("user_state")}
"""

    return f"<pre>{text}</pre>"


# ==========================================
# Показывает последние действия пользователя:
# сообщения, нажатия кнопок и ошибки.
# Используется для отладки.
# ==========================================
@app.route("/logs")
def show_logs():

    text = ""

    for l in logs[-30:]:

        if l["type"] == "message":
            text += f"📩 {l['text']}\n"

        elif l["type"] == "callback":
            text += f"🔘 {l['data']}\n"

        elif l["type"] == "error":
            text += f"❌ {l['error']}\n"

    return f"<pre>{text}</pre>"


if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, threaded=True)