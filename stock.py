import json
import os

FILE = "stock.json"


def load():

    if not os.path.exists(FILE):
        return {}

    with open(FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data):

    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def set_product(name, price=None, status=None):

    data = load()

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


def get_product(name):

    data = load()

    return data.get(name)


def get_all():

    return load()