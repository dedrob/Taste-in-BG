import requests


API = "https://www.themealdb.com/api/json/v1/1"


# ================= RECIPES BY INGREDIENTS =================

def recipes_by_ingredients(stock):

    if not stock:
        return []

    ingredients = []

    for name, info in stock.items():

        if info.get("status") == "have":
            ingredients.append(name)

    if not ingredients:
        return []

    ingredient = ingredients[0]

    url = f"{API}/filter.php?i={ingredient}"

    try:

        r = requests.get(url, timeout=10)

        data = r.json()

    except:

        return []

    if not data or not data.get("meals"):
        return []

    meals = []

    for m in data["meals"][:10]:

        meals.append({
            "id": m["idMeal"],
            "name": m["strMeal"],
            "image": m["strMealThumb"]
        })

    return meals


# ================= GET RECIPE =================

def get_recipe(recipe_id):

    url = f"{API}/lookup.php?i={recipe_id}"

    try:

        r = requests.get(url, timeout=10)

        data = r.json()

    except:

        return None

    if not data or not data.get("meals"):
        return None

    meal = data["meals"][0]

    ingredients = []

    for i in range(1, 21):

        ing = meal.get(f"strIngredient{i}")
        measure = meal.get(f"strMeasure{i}")

        if ing and ing.strip():

            if measure and measure.strip():
                ingredients.append(f"{ing} — {measure}")
            else:
                ingredients.append(ing)

    steps = meal.get("strInstructions", "").split(". ")

    return {
        "id": meal["idMeal"],
        "name": meal["strMeal"],
        "image": meal["strMealThumb"],
        "ingredients": ingredients,
        "steps": steps
    }