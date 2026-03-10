import os
import requests
import time
import random

from flask import Flask, request

from config import TOKEN, APPS_SCRIPT_URL
from data import load_data
data_cache = None
data_cache_time = 0
from catalog import get_categories, get_types, get_products
from recipes import recipes_by_ingredient, get_recipe
from stock import get_product, set_product, get_all
from translations import format_product_name, add_translation
from utils import emoji_for_product, extract_taste_emojis
from nlp_food import extract_ingredients
from search import search_products

from phrases import THINKING, FOUND, NOT_FOUND, ACTION, COOK, phrase


app = Flask(__name__)

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}"

user_state = {}

chat_memory = {}

last_bot_message = {}

ui_message = {}
# ================= Логи =================

logs = []

kitchen_history = []


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

def add_history(text):

    kitchen_history.append(text)

    if len(kitchen_history) > 20:
        kitchen_history.pop(0)
 
def load_data_cached():

    global data_cache, data_cache_time

    now = time.time()

    if data_cache and now - data_cache_time < 30:
        return data_cache

    data_cache = load_data()
    data_cache_time = now

    return data_cache   
    
# ================= TELEGRAM =================
# ==========================================
# Отправляет сообщение пользователю в Telegram.
# chat_id — ID пользователя
# text — текст сообщения
# keyboard — клавиатура (если нужно показать кнопки)
# ==========================================
def send(chat_id, text, reply=None, inline=None):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if reply:
        payload["reply_markup"] = reply

    if inline:
        payload["reply_markup"] = inline

    try:

        r = requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            json=payload
        )

        data = r.json()

        if data.get("ok"):
            last_bot_message[chat_id] = data["result"]["message_id"]

    except:
        pass
        
# Создать функцию UI-обновления       
def ui(chat_id, text, keyboard=None):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    # если UI уже есть — пробуем редактировать
    if chat_id in ui_message:

        try:
            edit(chat_id, ui_message[chat_id], text, keyboard)
            return
        except:
            pass

    # иначе отправляем новое
    r = requests.post(
        f"{TELEGRAM_URL}/sendMessage",
        json=payload
    )

    data = r.json()

    if data.get("ok"):
        ui_message[chat_id] = data["result"]["message_id"]
             
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

    try:
        requests.post(
            f"{TELEGRAM_URL}/editMessageText",
            json=payload
        )
    except:
        pass

# ================= KEYBOARDS =================
# ==========================================
# Редактирует уже отправленное сообщение.
# Используется для inline-кнопок.
# ==========================================
def translate_to_ru(text):

    if not text:
        return text

    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="auto", target="ru").translate(text)

    except Exception as e:
        print("translate error:", e)
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

# ================Добавить=продукт=============
def add_product_to_catalog(category, type_name, name, taste):

    payload = {
        "action": "add_product",
        "category": category,
        "type": type_name,
        "name": name,
        "taste": taste
    }

    requests.post(APPS_SCRIPT_URL, json=payload)

# ==========================================
# Бот отправляет случайную фразу «думаю...»
# и делает небольшую паузу.
# Это делает ответы более живыми.
# ==========================================
def show_menu(chat_id):

    buttons = [
        ["📂 Каталог"], 
        ["🍳 Что приготовить"],
        ["➕ Добавить продукты"],
        ["📦 Моя кухня"]
    ]

    send(chat_id, "Я на кухне. Что смотрим?", reply=reply_keyboard(buttons))

# Спрашивает пользователя добавить новый продукт в каталог
def ask_add_product(chat_id, name):

    buttons = [
        [
            {"text": "➕ Добавить", "callback_data": f"ADDNEW:{name}"},
            {"text": "❌ Нет", "callback_data": "ADDNEW:NO"}
        ]
    ]

    send(
        chat_id,
        f"Не нашла продукт.\n\n{name}\n\nДобавить в каталог?",
        inline=inline_keyboard(buttons)
    )
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

    ui(chat_id, "Выбирай категорию 👇", keyboard=reply_keyboard(buttons))

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

    ui(chat_id, category, keyboard=reply_keyboard(buttons))

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

        row.append(f"{emoji} {format_product_name(name)}")

        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    pages = max(1, (len(products) + per_page - 1) // per_page)

    nav = []

    if page > 0:
        nav.append("⬅")

    nav.append(f"{page+1}/{pages}")

    if page < pages - 1:
        nav.append("➡")

    buttons.append(nav)

    buttons.append(["⬅ Типы"])

    user_state.setdefault(chat_id, {})
    user_state[chat_id]["page"] = page

    ui(chat_id, phrase(FOUND), keyboard=reply_keyboard(buttons))

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

    send(chat_id, text, inline=inline_keyboard(buttons))

# ==========================================
# Показывает все продукты которые есть дома
# ==========================================
def show_kitchen(chat_id):

    stock = get_all()

    if not stock:
        send(chat_id, "На кухне пусто.")
        return

    have = []
    buy = []

    for name, data in stock.items():

        emoji = emoji_for_product(name)

        status = data.get("status")

        if status == "есть":
            have.append(f"{emoji} {format_product_name(name)}")

        elif status in ["мало", "купить"]:
            buy.append(f"{emoji} {format_product_name(name)}")

    text = ""

    if have:
        text += "📦 Есть:\n\n" + "\n".join(have)

    if buy:
        text += "\n\n🛒 Купить:\n\n" + "\n".join(buy)

    send(chat_id, text)

# Добавить функцию проверки ингредиентов
def analyze_recipe_ingredients(recipe):

    stock = get_all()

    have = []
    missing = []

    for i in range(1, 21):

        ing = recipe.get(f"strIngredient{i}")
        if not ing:
            continue

        ing = ing.strip().lower()

        if not ing:
            continue

        found = False

        for name, data in stock.items():

            name_clean = format_product_name(name).lower()

            if ing in name_clean or name_clean in ing:

                found = True
                break

        if found:
            have.append(ing)
        else:
            missing.append(ing)

    return have, missing

# Добавляем функцию извлечения ингредиентов рецепта
def get_recipe_ingredients(recipe):

    ingredients = []

    for i in range(1, 21):

        ing = recipe.get(f"strIngredient{i}")

        if not ing:
            continue

        ing = ing.strip()

        if ing:
            ingredients.append(ing)

    return ingredients
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

        send(chat_id, "Дома пусто")
        return

    send(chat_id, "Смотрю что можно приготовить...")

    found = []

    for ingredient in available:

        ingredient_en = format_product_name(ingredient)

        if "/" in ingredient_en:
            ingredient_en = ingredient_en.split("/")[-1].strip()

        recipes = recipes_by_ingredient(ingredient_en)

        if recipes:

            for r in recipes[:2]:
                found.append(r)

    if not found:

        send(chat_id, "Ну хер его что из этого можно сделать")
        return

    send(chat_id, phrase(COOK))

    shown = set()

    recipes_scored = []

    for r in found:

        recipe = get_recipe(r["idMeal"])

        if not recipe:
            continue

        have, missing = analyze_recipe_ingredients(recipe)

        recipes_scored.append((len(missing), r, recipe))

    recipes_scored.sort(key=lambda x: x[0])
    
    send(chat_id, random.choice([
        "Нашел рецепты 👇",
        "Вот что можно приготовить 👇",
        "Самые простые рецепты 👇"
    ]))
    
    for _, r, recipe in recipes_scored:

        if r["idMeal"] in shown:
            continue

        shown.add(r["idMeal"])

        title = translate_to_ru(recipe["strMeal"])

        have, missing = analyze_recipe_ingredients(recipe)

        text = f"🍳 {title}\n\n"

        if not missing:

            text += "всё есть ✅"

        else:

            if have:
                text += "есть:\n"
                text += "\n".join([f"{emoji_for_product(x)} {x}" for x in have])
                text += "\n\n"

            text += "не хватает:\n"
            text += "\n".join([f"• {x}" for x in missing])

        send(chat_id, text)

        if len(shown) >= 6:
            break

# Обрабатывает нажатия inline-кнопок.
def handle_callback(update):

    data_cb = update["callback_query"]["data"]

    chat_id = update["callback_query"]["message"]["chat"]["id"]
    
    log_event({
        "type": "callback",
        "chat_id": chat_id,
        "data": data_cb
    })
    
#название продукта → спрашиваем вкус и категорию    
    if data_cb.startswith("ADDNEW:"):

        value = data_cb.split(":")[1]

        if value == "NO":

            send(chat_id, "Ок. Не добавляем.")
            show_menu(chat_id)
            return

        user_state[chat_id] = {
            "adding_product": "taste",
            "name": value
        }

        send(chat_id, f"{value}\n\nНапиши вкус.")
        return
    
# REC: продукт → список рецептов
    if data_cb.startswith("REC:"):

        ingredient = data_cb.split(":")[1]

        thinking(chat_id)

        ingredient_en = format_product_name(ingredient)

        if "/" in ingredient_en:
            ingredient_en = ingredient_en.split("/")[-1].strip()

        recipes = recipes_by_ingredient(ingredient_en)

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

        send(chat_id, "Вот рецепты:", inline=inline_keyboard(buttons))

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
        buttons = [
        [
            {
            "text": "🛒 Добавить missing в покупки",
            "callback_data": f"ADD_RECIPE:{recipe_id}"
            }
        ]
    ]

        send(
            chat_id,
            text,
            inline=inline_keyboard(buttons)
    )

        send_photo(chat_id, photo)

        return

# добавить ингредиенты рецепта в кухню
    if data_cb.startswith("ADD_RECIPE:"):

        recipe_id = data_cb.split(":")[1]

        recipe = get_recipe(recipe_id)

        if not recipe:
            send(chat_id, "Не открывается")
            return

        added = []

        have, missing = analyze_recipe_ingredients(recipe)

        for ing in missing:

            set_product(ing, status="есть")

            emoji = emoji_for_product(ing)

            added.append(f"{emoji} {ing}")

            add_history(f"Добавил из рецепта: {ing}")

        send(
            chat_id,
            "Добавил ингредиенты:\n\n" + "\n".join(added)
        )

        return


# STOCK → изменить статус продукта
    if data_cb.startswith("STOCK:"):

        _, name, status = data_cb.split(":")

        set_product(name, status=status)

        send(chat_id, phrase(ACTION))

        return


# TR → добавить перевод
    if data_cb.startswith("TR:"):

        name = data_cb.split(":")[1]

        user_state[chat_id] = {"translate_product": name}

        send(chat_id, "Напиши перевод")

        return
 
 
# Отправка сообщения с автоудалением

# Главная функция обработки сообщений.
# Определяет что написал пользователь:
def handle_message(update):

    message = update["message"]
    chat_id = message["chat"]["id"]

    text = message.get("text", "").strip()
    lower = text.lower()

    # ================= ПАМЯТЬ =================

    memory = chat_memory.setdefault(chat_id, [])
    memory.append(lower)

    if len(memory) > 5:
        memory.pop(0)

    # ================= ЛОГ =================

    log_event({
        "type": "message",
        "chat_id": chat_id,
        "text": text
    })

    # ================= ЗАГРУЗКА ДАННЫХ =================
    data = load_data_cached()

    # ================= ПЕРЕВОД ПРОДУКТА =================

    if chat_id in user_state and "translate_product" in user_state[chat_id]:

        product = user_state[chat_id]["translate_product"]

        add_translation(product, text)

        send(chat_id, f"Сохранил перевод:\n{product} ({text})")

        user_state.pop(chat_id)

        return

    # ================= СТАРТ =================

    if text == "/start":

        show_menu(chat_id)
        return

    # ================= МЕНЮ =================

    # Меню, категории, типы, продукты — это основная навигация по каталогу.
    if text == "📂 Каталог":

        thinking(chat_id)
        show_categories(chat_id, data)
        return
    # ================= ЧТО ПРИГОТОВИТЬ =================
    if text == "🍳 Что приготовить":

        thinking(chat_id)
        cook_assistant(chat_id)
        return

    # ================= МОЯ КУХНЯ =================
    if text == "📦 Моя кухня":

        thinking(chat_id)
        show_kitchen(chat_id)
        return

    # ================= МАССОВОЕ ДОБАВЛЕНИЕ =================

    if text == "➕ Добавить продукты":

        user_state[chat_id] = {"bulk_add": True}

        send(chat_id, "Пиши продукты по одному.\n\nНапиши 'стоп' чтобы закончить.")

        return

    # ================= РЕЖИМ МАССОВОГО ДОБАВЛЕНИЯ =================

    if chat_id in user_state and user_state[chat_id].get("bulk_add"):

        if lower in ["стоп", "хватит", "готово"]:

            user_state.pop(chat_id)

            send(chat_id, "Ок, закончили.")
            return

        name = text.strip()

        ask_add_product(chat_id, name)

        return

    # ================= НАЗАД =================
    
    # кнопки "назад" для удобной навигации по меню.
    if text == "⬅ Меню":

        show_menu(chat_id)
        user_state.pop(chat_id, None)
        return

    # кнопки "назад" для удобной навигации по меню.
    if text == "⬅ Категории":

        show_categories(chat_id, data)
        user_state.pop(chat_id, None)
        return

    # кнопки "назад" для удобной навигации по меню.
    if text == "⬅ Типы":

        if chat_id in user_state and "category" in user_state[chat_id]:

            show_types(chat_id, data, user_state[chat_id]["category"])
            user_state[chat_id].pop("type", None)

        return

   
    # ================= КАТЕГОРИИ =================

    categories = get_categories(data)

    if text in categories:

        thinking(chat_id)

        user_state[chat_id] = {
            "category": text
        }

        show_types(chat_id, data, text)
        return

    # ================= ТИПЫ =================

    if chat_id in user_state and "category" in user_state[chat_id]:

        category = user_state[chat_id]["category"]

        types = get_types(data, category)

        if text in types:

            thinking(chat_id)

            user_state[chat_id]["type"] = text

            show_products(chat_id, data, category, text)
            return

    # ================= ОТКРЫТИЕ ПРОДУКТА =================

    if chat_id in user_state and "type" in user_state[chat_id]:

        category = user_state[chat_id]["category"]
        type_name = user_state[chat_id]["type"]

        products = get_products(data, category, type_name)

        for r in products:

            if len(r) < 6:
                continue

            name = r[5]

            clean = text.split(" ", 1)[-1].lower()

            if name.lower() == clean:

                thinking(chat_id)
                show_product(chat_id, r)
                return

    # ================= ДОБАВЛЕНИЕ ПРОДУКТОВ =================

    if lower.startswith("добавь ") or lower.startswith("добавить "):

        items = text.split(" ", 1)[1]

        items = [
            x for x in items.replace(",", " ").split()
            if x.lower() not in ["и","and"]
        ]

        added = []

        for item in items:

            results = search_products(item, data)

            if results:

                name = None

                for r in results:

                    candidate = r[5].lower()

                    if candidate == item.lower():
                        name = r[5]
                        break

                if not name:
                    name = results[0][5]

                set_product(name, status="есть")

                emoji = emoji_for_product(name)

                added.append(f"{emoji} {name}")

                add_history(f"Добавил: {name}")

            else:

                ask_add_product(chat_id, item)
                return

        if added:
            send(chat_id, "Добавил.\n\n" + "\n".join(added))

        return

    
    # ================= УДАЛИТЬ ПРОДУКТ =================

    if lower.startswith("удали"):

        item = text.replace("удали", "").strip()

        if not item:
            send(chat_id, "Что удалить?")
            return

        results = search_products(item, data)

        if not results:

            send(chat_id, "Не нашла такой продукт.")
            return

        name = results[0][5]

        stock = get_all()

        if name not in stock:

            send(chat_id, "Этого продукта нет на кухне.")
            return

        stock.pop(name)

        import json

        with open("stock.json", "w", encoding="utf-8") as f:
            json.dump(stock, f, ensure_ascii=False, indent=2)

        emoji = emoji_for_product(name)

        send(chat_id, f"Убрала:\n\n{emoji} {name}")

        add_history(f"Удалил: {name}")

        return
    
    # ================= КУПИЛ =================

    if lower.startswith("купил ") or lower.startswith("купила "):

        items = text.split(" ", 1)[1]

        items = [
            x for x in items.replace(",", " ").split()
            if x.lower() not in ["и","and"]
        ]

        updated = []

        for item in items:

            results = search_products(item, data)

            if results:

                name = None

                for r in results:

                    candidate = r[5].lower()

                    if candidate == item.lower():
                        name = r[5]
                        break

                if not name:
                    name = results[0][5]

                set_product(name, status="есть")

                emoji = emoji_for_product(name)

                updated.append(f"{emoji} {name}")

                add_history(f"Купила: {name}")

        if updated:
            send(chat_id, "Отметила.\n\n" + "\n".join(updated))

        return

    # ================= ЗАКОНЧИЛОСЬ =================

    if "закончил" in lower:

        items = text.split(" ", 1)[1]

        items = [
            x for x in items.replace(",", " ").split()
            if x.lower() not in ["и","and"]
        ]

        updated = []

        for item in items:

            results = search_products(item, data)

            if results:

                name = None

                for r in results:

                    candidate = r[5].lower()

                    if candidate == item.lower():
                        name = r[5]
                        break

                if not name:
                    name = results[0][5]

                set_product(name, status="купить")

                emoji = emoji_for_product(name)

                updated.append(f"{emoji} {name}")

                add_history(f"Закончился: {name}")

        if updated:
            send(chat_id, "Записала.\n\n" + "\n".join(updated))

        return

    # ================= ЧТО ЕСТЬ =================

    if lower in ["что есть", "холодильник", "что дома"]:

        stock = get_all()

        items = []

        for name, data in stock.items():

            if data.get("status") == "есть":

                emoji = emoji_for_product(name)

                items.append(f"{emoji} {format_product_name(name)}")

        if not items:
            send(chat_id, "На кухне пусто.")
            return

        send(chat_id, "📦 Есть:\n\n" + "\n".join(items))

        return
    
    # ================= ЧТО ЗАКАНЧИВАЕТСЯ =================

    if lower in ["что заканчивается", "что скоро закончится"]:

        stock = get_all()

        items = []

        for name, data in stock.items():

            if data.get("status") == "мало":

                emoji = emoji_for_product(name)

                items.append(f"{emoji} {format_product_name(name)}")

        if not items:
            send(chat_id, "Ща пока норм")
            return

        send(chat_id, "⚠ Заканчивается:\n\n" + "\n".join(items))

        return
    
    # ================= ЗАКУПКА =================

    if lower in ["закупка", "магазин"]:

        stock = get_all()

        items = []

        for name, data in stock.items():

            if data.get("status") in ["мало", "купить"]:

                emoji = emoji_for_product(name)

                items.append(f"{emoji} {format_product_name(name)}")

        if not items:
            send(chat_id, "Сиди дома, ничего покупать не нужно")
            return

        send(chat_id, "🛒 Закупка:\n\n" + "\n".join(items))

        return
    
    # ================= БЫСТРЫЕ КОМАНДЫ =================

    if text.startswith("+"):

        name = text[1:].strip()

        results = search_products(name, data)

        if results:

            name = results[0][5]

            set_product(name, status="есть")

            send(chat_id, f"Добавил {name}")

        return


    if text.startswith("-"):

        name = text[1:].strip()

        results = search_products(name, data)

        if results:

            name = results[0][5]

            set_product(name, status="купить")

            send(chat_id, f"Закончился {name}")

        return
    
    # ================= NLP =================

    ingredients = extract_ingredients(text)

    if ingredients and len(ingredients) <= 5:

        updated = []

        for ing in ingredients:

            if ing.isdigit():
                continue

            set_product(ing, status="есть")

            emoji = emoji_for_product(ing)

            updated.append(f"{emoji} {ing}")

        if updated:
            send(chat_id, "Добавил:\n\n" + "\n".join(updated))

        return

    # ================= ПОИСК =================

    results = search_products(text, data)

    if results:

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

        send(chat_id, "Вот что нашёл", reply=reply_keyboard(buttons))
        return
# ================= НЕИЗВЕСТНЫЙ ПРОДУКТ =================

# если текст похож на название продукта
    words = text.replace(",", " ").split()

    # фильтр коротких сообщений
    if 1 <= len(words) <= 3:

        candidate = text.lower()

        # фильтр команд
        blacklist = [
            "что",
            "как",
            "где",
            "почему",
            "когда",
            "меню",
            "каталог",
            "кухня",
            "рецепт",
            "добавь",
            "купил",
            "купила",
            "закончился",
            "закончились"
        ]

        if candidate not in blacklist:

            ask_add_product(chat_id, text)

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

    update = request.get_json(silent=True)

    if not update:
        return "ok"

    try:

        if "message" in update:
            handle_message(update)

        if "callback_query" in update:
            handle_callback(update)

    except Exception as e:

        print("ERROR:", e)

        log_event({
            "type": "error",
            "error": str(e)
        })

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
        data = load_data_cached()
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)