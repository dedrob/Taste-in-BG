import requests

BASE_URL = "https://www.themealdb.com/api/json/v1/1/"


# поиск рецептов по ингредиенту
def recipes_by_ingredient(ingredient):

    url = BASE_URL + f"filter.php?i={ingredient}"

    r = requests.get(url)
    data = r.json()

    if not data["meals"]:
        return []

    return data["meals"][:6]


# получить полный рецепт
def get_recipe(recipe_id):

    url = BASE_URL + f"lookup.php?i={recipe_id}"

    r = requests.get(url)
    data = r.json()

    if not data["meals"]:
        return None

    return data["meals"][0]