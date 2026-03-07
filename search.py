from config import SEARCH_LIMIT


# ================= LEVENSHTEIN =================

def levenshtein(a, b):

    if len(a) < len(b):
        return levenshtein(b, a)

    if len(b) == 0:
        return len(a)

    previous_row = list(range(len(b) + 1))

    for i, c1 in enumerate(a):

        current_row = [i + 1]

        for j, c2 in enumerate(b):

            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)

            current_row.append(min(insertions, deletions, substitutions))

        previous_row = current_row

    return previous_row[-1]


# ================= PREFIX CHECK =================

def similar_prefix(a, b):

    if len(a) < 2 or len(b) < 2:
        return True

    return a[0] == b[0]


# ================= SEARCH =================

def search_products(query, data):

    query = query.lower().strip()

    results = []

    for row in data:

        name = row[5].lower()

        words = name.split()

        best = 999

        for w in words:

            if query in w:
                best = 0
                break

            if not similar_prefix(query, w):
                continue

            d = levenshtein(query, w)

            if d < best:
                best = d

        if best <= 2:

            results.append((best, row))

    results.sort(key=lambda x: x[0])

    return [r[1] for r in results[:SEARCH_LIMIT]]