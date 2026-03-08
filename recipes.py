import requests


API = "https://www.themealdb.com/api/json/v1/1"


def recipes_by_ingredient(ingredient):

    url = f"{API}/filter.php?i={ingredient}"

    r = requests.get(url)

    try:
        data = r.json()
    except:
        return []

    if not data or not data["meals"]:
        return []

    return data["meals"][:10]


def get_recipe(recipe_id):

    url = f"{API}/lookup.php?i={recipe_id}"

    r = requests.get(url)

    data = r.json()

    if not data or not data["meals"]:
        return None

    return data["meals"][0]