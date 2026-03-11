import re


# =========================
# WORD DICTIONARIES
# =========================

ADD_WORDS = [
    "купил", "купила", "купить",
    "добавь", "добавила", "добавить",
    "есть", "имеется", "взял", "взяла"
]

REMOVE_WORDS = [
    "убери", "удали", "выкинь",
    "нет", "закончился", "закончилась"
]

CATALOG_WORDS = [
    "каталог", "продукты", "покажи продукты"
]

RECIPE_WORDS = [
    "что приготовить",
    "что можно приготовить",
    "что сделать",
    "рецепт"
]


# =========================
# EXTRACT INGREDIENTS
# =========================

def extract_ingredients(text):

    text = text.lower()

    patterns = [
        r"из ([а-яa-z ]+)",
        r"с ([а-яa-z ]+)",
        r"есть ([а-яa-z ]+)"
    ]

    ingredients = []

    for p in patterns:

        match = re.search(p, text)

        if match:

            words = match.group(1)

            parts = re.split(r",|и| ", words)

            for w in parts:

                w = w.strip()

                if len(w) > 2:
                    ingredients.append(w)

    return list(set(ingredients))


# =========================
# SIMPLE INGREDIENT SPLIT
# =========================

def extract_words(text):

    words = re.split(r"[ ,.!?]", text)

    result = []

    for w in words:

        w = w.strip()

        if len(w) > 2:
            result.append(w)

    return list(set(result))


# =========================
# DETECT ACTION
# =========================

def detect_action(text):

    text = text.lower().strip()

    ingredients = extract_ingredients(text)

    words = extract_words(text)


    # =========================
    # RECIPES
    # =========================

    for r in RECIPE_WORDS:

        if r in text:

            if ingredients:
                return "SEARCH_RECIPES_BY_INGREDIENTS", ingredients

            return "FIND_RECIPES", None


    # =========================
    # CATALOG
    # =========================

    for c in CATALOG_WORDS:

        if c in text:
            return "OPEN_CATALOG", None


    # =========================
    # REMOVE PRODUCTS
    # =========================

    for w in REMOVE_WORDS:

        if w in text:

            if ingredients:
                return "REMOVE_PRODUCTS", ingredients

            return "REMOVE_PRODUCTS", words


    # =========================
    # ADD PRODUCTS
    # =========================

    for w in ADD_WORDS:

        if w in text:

            if ingredients:
                return "ADD_PRODUCTS", ingredients

            return "ADD_PRODUCTS", words


    # =========================
    # PRODUCT SEARCH
    # =========================

    if len(words) == 1:

        return "SEARCH_PRODUCTS", words[0]


    if ingredients:

        return "SEARCH_PRODUCTS", ingredients[0]


    return "UNKNOWN", None