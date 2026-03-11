import json
import os

from data import normalize_ingredient


FILE = "stock.json"


# ================= LOAD =================

def load():
    try:
        if not os.path.exists(FILE):
            return {}

        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading stock data: {e}")
        return {}


# ================= SAVE =================

def save(data):
    try:
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Stock data saved successfully.")
    except Exception as e:
        print(f"Error saving stock data: {e}")


# ================= ADD PRODUCTS =================

def add_products(products):

    data = load()

    for p in products:

        p = normalize_ingredient(p)

        if p not in data:

            data[p] = {
                "price": None,
                "status": "have"
            }

        else:

            data[p]["status"] = "have"

    save(data)


# ================= REMOVE PRODUCTS =================

def remove_products(products):

    data = load()

    for p in products:

        p = normalize_ingredient(p)

        if p in data:

            data[p]["status"] = "none"

    save(data)


# ================= SET PRODUCT =================

def set_product(name, price=None, status=None):

    data = load()

    name = normalize_ingredient(name)

    if name not in data:

        data[name] = {
            "price": None,
            "status": None
        }

    if price is not None:
        data[name]["price"] = price

    if status is not None:
        data[name]["status"] = status

    save(data)


# ================= GET PRODUCT =================

def get_product(name):

    data = load()

    name = normalize_ingredient(name)

    return data.get(name)


# ================= GET ALL =================

def get_all():

    return load()