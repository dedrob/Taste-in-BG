import requests
import csv
import io
import time

from config import GOOGLE_SHEET_URL, CACHE_TTL


_cache = None
_cache_time = 0
_index = {}


# ================= LOAD DATA =================

def load_data():

    global _cache, _cache_time

    now = time.time()

    if _cache and now - _cache_time < CACHE_TTL:
        return _cache
    try:
        response = requests.get(GOOGLE_SHEET_URL, timeout=10)
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

        words = row[5].lower().split()

        for word in words:

            if word not in _index:
                _index[word] = []

            _index[word].append(row)


# ================= GET INDEX =================

def get_index():

    return _index