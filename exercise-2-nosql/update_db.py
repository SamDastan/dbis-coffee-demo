from tinydb import TinyDB

db = TinyDB('coffee_db.json')

# The missing recipes identified from the CSV
missing_recipes = [
    {
        "id": "espresso",
        "name": "Espresso",
        "category": "Espresso",
        "time_minutes": 2,
        "servings": 1,
        "ingredients": [{"item": "Coffee beans", "amount": 18, "unit": "g"}],
        "equipment": ["Espresso machine"],
        "steps": ["Grind beans", "Brew 30ml shot"]
    },
    {
        "id": "cappuccino",
        "name": "Cappuccino",
        "category": "Cappuccino",
        "time_minutes": 6,
        "servings": 1,
        "ingredients": [{"item": "Espresso", "amount": 1, "unit": "shot"}, {"item": "Milk", "amount": 150, "unit": "ml"}],
        "equipment": ["Espresso machine", "Steam wand"],
        "steps": ["Brew espresso", "Steam milk to thick foam", "Pour over espresso"]
    }
]

db.insert_multiple(missing_recipes)
print("Task 2b: Successfully added missing recipes to coffee_db.json")