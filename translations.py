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

def get_translation(name):

    try:

        with open("translations.json", encoding="utf-8") as f:
            data = json.load(f)

        return data.get(name)

    except:
        return None


# ================= ADD =================

def add_translation(product, translation):

    translations[product] = translation

    save_translations()


# ================= FORMAT =================

def format_product_name(name):

    translation = get_translation(name)

    if translation:
        return f"{name} ({translation})"

    return name


# ================= INIT =================
load_translations()