import requests
import csv
import io
import time

from config import GOOGLE_SHEET_URL, CACHE_TTL


_cache = None
_cache_time = 0
_index = {}

_ingredient_map = None


# ================= LOAD DATA =================

def load_data():

    global _cache, _cache_time

    now = time.time()

    if _cache and now - _cache_time < CACHE_TTL:
        return _cache

    try:

        response = requests.get(GOOGLE_SHEET_URL, timeout=10)

        if response.status_code != 200:
            return _cache if _cache else []

    except:

        return _cache if _cache else []

    content = response.content.decode("utf-8")

    reader = csv.reader(io.StringIO(content))

    next(reader)

    data = []

    for i, row in enumerate(reader, start=2):

        if len(row) >= 6:

            data.append([
                i,              # row number
                row[0].strip(), # category
                row[1].strip(), # category emoji
                row[2].strip(), # type
                row[3].strip(), # type emoji
                row[4].strip(), # product
                row[5].strip()  # taste
            ])

    _cache = data
    _cache_time = now

    build_index(data)

    return data


# ================= BUILD INDEX =================

def build_index(data):

    global _index

    _index = {}

    for row in data:

        product = row[5].lower()

        words = product.split()

        for word in words:

            if word not in _index:
                _index[word] = []

            _index[word].append(row)


# ================= GET INDEX =================

def get_index():

    if not _index:
        load_data()

    return _index


# ================= LOAD INGREDIENT MAP =================

def load_ingredient_map():

    from config import GOOGLE_SHEET_URL

    url = GOOGLE_SHEET_URL + "&gid=1945827954"

    try:

        response = requests.get(url, timeout=10)

    except:

        return {}

    content = response.content.decode("utf-8")

    reader = csv.reader(io.StringIO(content))

    next(reader)

    mapping = {}

    for row in reader:

        if len(row) < 2:
            continue

        synonyms = row[0].lower().split(",")

        ingredient_en = row[1].strip().lower()

        for s in synonyms:

            mapping[s.strip()] = ingredient_en

    return mapping


# ================= GET INGREDIENT MAP =================

def get_ingredient_map():

    global _ingredient_map

    if _ingredient_map:
        return _ingredient_map

    _ingredient_map = load_ingredient_map()

    return _ingredient_map


# ================= NORMALIZE INGREDIENT =================

def normalize_ingredient(word):

    word = word.lower().strip()

    mapping = get_ingredient_map()

    if word in mapping:
        return mapping[word]

    return word