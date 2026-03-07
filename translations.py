import json
import os


TRANSLATION_FILE = "translations.json"

translations = {}


# ================= LOAD =================

def load_translations():

    global translations

    if not os.path.exists(TRANSLATION_FILE):

        translations = {}
        return

    with open(TRANSLATION_FILE, "r", encoding="utf-8") as f:

        translations = json.load(f)


# ================= SAVE =================

def save_translations():

    with open(TRANSLATION_FILE, "w", encoding="utf-8") as f:

        json.dump(translations, f, ensure_ascii=False, indent=2)


# ================= GET =================

def get_translation(product):

    return translations.get(product)


# ================= ADD =================

def add_translation(product, translation):

    translations[product] = translation

    save_translations()


# ================= FORMAT =================

def format_product_name(product):

    tr = get_translation(product)

    if tr:

        return f"{product} / {tr}"

    return product


# ================= INIT =================

load_translations()