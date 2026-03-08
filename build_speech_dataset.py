import zipfile
import re
from html import unescape

ZIP_FILE = "speech_source.zip"
OUT_FILE = "speech_db.py"


def clean_html(text):

    text = unescape(text)

    # убираем html
    text = re.sub(r"<.*?>", " ", text)

    # нормализуем пробелы
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_phrases(text):

    # убираем ссылки
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"www\S+", " ", text)

    # убираем эмодзи и спецсимволы
    text = re.sub(r"[^\w\sа-яёіїєґ]", " ", text)

    # нормализуем пробелы
    text = re.sub(r"\s+", " ", text).lower()

    phrases = []

    # ищем фразы 1–6 слов из кириллицы
    matches = re.findall(r"(?:[а-яёіїєґ]{1,20}\s?){1,6}", text)

    for m in matches:

        p = m.strip()

        if not p:
            continue

        if len(p) > 80:
            continue

        phrases.append(p)

    return phrases

def classify(p):

    if any(w in p for w in ["сек", "щас", "сейчас", "гляну", "подожди"]):
        return "thinking"

    if any(w in p for w in ["нашёл", "нашла", "вот", "смотри"]):
        return "found"

    if any(w in p for w in ["рецепт", "приготов", "сварить", "сделать"]):
        return "recipes"

    if any(w in p for w in ["нет", "ничего", "не нашёл", "не вижу"]):
        return "error"

    return "reaction"


def main():

    groups = {
        "thinking": set(),
        "reaction": set(),
        "found": set(),
        "recipes": set(),
        "error": set()
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
_last = {}

def phrase(group):

    options = PHRASES.get(group, [])

    if not options:
        return ""

    import random

    last = _last.get(group)

    choices = [o for o in options if o != last]

    if not choices:
        choices = options

    pick = random.choice(choices)

    _last[group] = pick

    return pick
""")

    print("speech_db.py создан")


if __name__ == "__main__":
    main()