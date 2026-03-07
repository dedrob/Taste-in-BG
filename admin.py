<<<<<<< HEAD
import requests

from config import APPS_SCRIPT_URL


# ================= UPDATE TASTE =================

def update_taste(row, taste):

    payload = {
        "action": "update_taste",
        "row": row,
        "taste": taste
    }

    requests.post(APPS_SCRIPT_URL, json=payload)


# ================= ADD PRODUCT =================

def add_product(category, category_emoji, type_name, type_emoji, product, taste):

    payload = {
        "action": "add_product",
        "category": category,
        "category_emoji": category_emoji,
        "type": type_name,
        "type_emoji": type_emoji,
        "product": product,
        "taste": taste
    }

    requests.post(APPS_SCRIPT_URL, json=payload)


# ================= UPDATE PRODUCT =================

def update_product(row, category, type_name, product, taste):

    payload = {
        "action": "update_product",
        "row": row,
        "category": category,
        "type": type_name,
        "product": product,
        "taste": taste
    }

    requests.post(APPS_SCRIPT_URL, json=payload)


# ================= DELETE PRODUCT =================

def delete_product(row):

    payload = {
        "action": "delete_product",
        "row": row
    }

    requests.post(APPS_SCRIPT_URL, json=payload)


# ================= RENAME PRODUCT =================

def rename_product(row, new_name):

    payload = {
        "action": "rename_product",
        "row": row,
        "name": new_name
    }

=======
import requests

from config import APPS_SCRIPT_URL


# ================= UPDATE TASTE =================

def update_taste(row, taste):

    payload = {
        "action": "update_taste",
        "row": row,
        "taste": taste
    }

    requests.post(APPS_SCRIPT_URL, json=payload)


# ================= ADD PRODUCT =================

def add_product(category, category_emoji, type_name, type_emoji, product, taste):

    payload = {
        "action": "add_product",
        "category": category,
        "category_emoji": category_emoji,
        "type": type_name,
        "type_emoji": type_emoji,
        "product": product,
        "taste": taste
    }

    requests.post(APPS_SCRIPT_URL, json=payload)


# ================= UPDATE PRODUCT =================

def update_product(row, category, type_name, product, taste):

    payload = {
        "action": "update_product",
        "row": row,
        "category": category,
        "type": type_name,
        "product": product,
        "taste": taste
    }

    requests.post(APPS_SCRIPT_URL, json=payload)


# ================= DELETE PRODUCT =================

def delete_product(row):

    payload = {
        "action": "delete_product",
        "row": row
    }

    requests.post(APPS_SCRIPT_URL, json=payload)


# ================= RENAME PRODUCT =================

def rename_product(row, new_name):

    payload = {
        "action": "rename_product",
        "row": row,
        "name": new_name
    }

>>>>>>> f80c4aceb3fa4f4de35edb071a8561d63341e3b7
    requests.post(APPS_SCRIPT_URL, json=payload)