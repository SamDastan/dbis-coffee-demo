import json
from tinydb import TinyDB

# 1. Initialize the TinyDB file
db = TinyDB('coffee_db.json')

# 2. Clear any old data just in case
db.truncate()

# 3. Load and parse the JSON file
try:
    with open('coffee_recipes.json', 'r') as f:
        data = json.load(f)
    
    # We access the "recipes" list inside your JSON
    recipe_list = data["recipes"]
    
    # 4. Insert each recipe as its own document
    db.insert_multiple(recipe_list)

    print("--- Success ---")
    print(f"Database 'coffee_db.json' created.")
    print(f"Total recipes imported: {len(db)}")

except FileNotFoundError:
    print("Error: Could not find 'coffee_recipes.json'. Check the filename!")
except KeyError:
    print("Error: The JSON file doesn't have a 'recipes' key.")