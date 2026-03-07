import re


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