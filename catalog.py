from config import PAGE_SIZE


# ================= CATEGORIES =================

def get_categories(data):

    categories = {}

    for row in data:

        category = row[1]
        emoji = row[2]

        categories[category] = emoji

    return categories


# ================= TYPES =================

def get_types(data, category):

    types = {}

    for row in data:

        if row[1] != category:
            continue

        type_name = row[3]
        emoji = row[4]

        types[type_name] = emoji

    return types


# ================= PRODUCTS =================

def get_products(data, category, type_name):

    products = []

    for row in data:

        if row[1] == category and row[3] == type_name:

            products.append(row)

    return products


# ================= PAGINATION =================

def paginate(items, page):

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE

    return items[start:end]


def total_pages(items):

    if not items:
        return 1

    return (len(items) - 1) // PAGE_SIZE + 1