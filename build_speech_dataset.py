import zipfile
import re
from html import unescape

ZIP_FILE = "speech_source.zip"
OUT_FILE = "speech_db.py"


def clean_html(text):

    text = unescape(text)
    text = re.sub(r"<.*?>", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_phrases(text):

    parts = re.split(r"[.!?\n]", text)

    phrases = []

    for p in parts:

        p = p.strip().lower()

        if len(p) < 2:
            continue

        if len(p) > 120:
            continue

        # пропускаем чисто цифры
        if p.isdigit():
            continue

        # пропускаем почти цифры
        if re.match(r"^[0-9\s]+$", p):
            continue

        phrases.append(p)

    return phrases


def classify(p):

    if len(p.split()) <= 2:
        return "reaction"

    if any(w in p for w in ["щас", "сек", "сейчас", "гляну", "посмотрю"]):
        return "thinking"

    if any(w in p for w in ["рецепт", "приготов", "сделать"]):
        return "recipes"

    if any(w in p for w in ["куп", "взять"]):
        return "buy"

    return "general"


def main():

    groups = {
        "reaction": set(),
        "thinking": set(),
        "recipes": set(),
        "buy": set(),
        "low": set(),
        "have": set(),
        "general": set()
    }

    with zipfile.ZipFile(ZIP_FILE, "r") as z:

        for name in z.namelist():

            if not name.endswith(".html"):
                continue

            data = z.read(name).decode("utf-8", errors="ignore")

            text = clean_html(data)

            phrases = split_phrases(text)

            for p in phrases:

                cat = classify(p)

                groups[cat].add(p)

    with open(OUT_FILE, "w", encoding="utf-8") as f:

        f.write("import random\n\n")

        f.write("PHRASES = {\n")

        for cat, phrases in groups.items():

            f.write(f'    "{cat}": [\n')

            for p in sorted(phrases):

                p = p.replace('"', "'")

                f.write(f'        "{p}",\n')

            f.write("    ],\n")

        f.write("}\n\n")

        f.write("""
def phrase(group):

    options = PHRASES.get(group, [])

    if not options:
        return ""

    return random.choice(options)
""")

    print("speech_db.py создан")


if __name__ == "__main__":
    main()