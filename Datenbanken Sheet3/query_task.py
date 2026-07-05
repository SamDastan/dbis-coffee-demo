from tinydb import TinyDB, Query

db = TinyDB('coffee_db.json')
Recipe = Query()

result = db.search(Recipe.name == "Americano with Milk")

if result:
    recipe = result[0]  
    print("\n--- TASK 1d RESULT ---")
    print(f"Ingredients for {recipe['name']}:")
    
    for ing in recipe['ingredients']:
        print(f"- {ing['amount']} {ing['unit']} of {ing['item']}")