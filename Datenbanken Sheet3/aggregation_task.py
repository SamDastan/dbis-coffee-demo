import csv
from tinydb import TinyDB

# 1. Load preparation times from TinyDB into a dictionary for fast lookup
db = TinyDB('coffee_db.json')
prep_times = {recipe['name']: recipe['time_minutes'] for recipe in db.all()}

daily_totals = {}

# 2. Open and read the relational CSV data
with open('Coffe_sales.csv', mode='r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        date = row['Date']
        coffee = row['coffee_name']
        
        # Get the time for this specific coffee from our lookup dictionary
        minutes = prep_times.get(coffee, 0)
        
        # Accumulate the time per date
        daily_totals[date] = daily_totals.get(date, 0) + minutes

# 3. Print the final result
print("\n--- TASK 2c RESULT: Aggregated Time Per Day ---")
print(f"{'Date':<12} | {'Total Minutes':<15}")
print("-" * 30)
for date in sorted(daily_totals.keys()):
    print(f"{date:<12} | {daily_totals[date]:<15}")