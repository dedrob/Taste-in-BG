# ================= PRODUCT EMOJI =================

PRODUCT_KEYWORDS = [
    ("бекон", "🥓"),
    ("колбас", "🌭"),
    ("куриц", "🍗"),
    ("говядин", "🥩"),
    ("свинин", "🥩"),
    ("лосос", "🐟"),
    ("тунец", "🐟"),
    ("кревет", "🦐"),
    ("сыр", "🧀"),
    ("шокол", "🍫"),
    ("печенье", "🍪"),
    ("йогурт", "🥣"),
    ("молоко", "🥛"),
    ("банан", "🍌"),
    ("яблок", "🍎"),
    ("виноград", "🍇")
]


def emoji_for_product(name, fallback="🍽"):

    text = name.lower()

    for key, emoji in PRODUCT_KEYWORDS:

        if key in text:
            return emoji

    return fallback


# ================= TASTE EMOJI =================

TASTE_EMOJI = {
    "слад": "🍬",
    "сол": "🧂",
    "копч": "🔥",
    "остр": "🌶",
    "кисл": "🍋",
    "горь": "☕",
    "сливоч": "🥛",
    "шокол": "🍫",
    "освеж": "❄",
    "насыщ": "💥"
}


def extract_taste_emojis(description):

    text = description.lower()

    found = []

    for key, emoji in TASTE_EMOJI.items():

        if key in text and emoji not in found:

            found.append(emoji)

    return " ".join(found[:3])