import csv
import psycopg2

connection = psycopg2.connect(
    dbname="coffee_forecasting",
    user="nousha",
    password="",
    host="localhost",
    port="5432"
)

cursor = connection.cursor()

cursor.execute("DROP TABLE IF EXISTS sales")

cursor.execute("""
CREATE TABLE sales (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    time TIME,
    coffee_name TEXT NOT NULL,
    money NUMERIC,
    cash_type TEXT
)
""")

with open("Coffe_sales.csv", mode="r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        cursor.execute("""
            INSERT INTO sales (date, time, coffee_name, money, cash_type)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            row["Date"],
            row["Time"],
            row["coffee_name"],
            row["money"] if row.get("money") else None,
            row.get("cash_type", "")
        ))

connection.commit()

cursor.execute("SELECT COUNT(*) FROM sales")
count = cursor.fetchone()[0]

cursor.close()
connection.close()

print("Created Postgres table: sales")
print("Imported sales rows:", count)