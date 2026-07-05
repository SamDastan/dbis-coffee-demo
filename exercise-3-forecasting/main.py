import psycopg2
from tinydb import TinyDB
from collections import defaultdict
from datetime import timedelta

import pandas as pd
import matplotlib.pyplot as plt

from forecasting import forecast_future, rolling_evaluation_forecast


def load_recipes_from_tinydb():
    db = TinyDB("coffee_db.json")

    recipes = {
        recipe["name"]: recipe["ingredients"]
        for recipe in db.all()
    }

    return recipes


def load_sales_from_postgres():
    connection = psycopg2.connect(
        dbname="coffee_forecasting",
        user="nousha",
        password="",
        host="localhost",
        port="5432"
    )

    cursor = connection.cursor()

    cursor.execute("""
        SELECT date, coffee_name
        FROM sales
        ORDER BY date
    """)

    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return rows


def load_daily_ingredient_usage():
    recipes = load_recipes_from_tinydb()
    sales = load_sales_from_postgres()

    daily_usage = defaultdict(lambda: defaultdict(float))

    for date, coffee_name in sales:
        date = str(date)

        if coffee_name not in recipes:
            print("Missing recipe for:", coffee_name)
            continue

        for ingredient in recipes[coffee_name]:
            item = ingredient["item"]
            amount = float(ingredient["amount"])

            # Required assumption:
            # The recipe Cocoa contains "Milk or water".
            # For the forecasting task, this choice is treated as Milk.
            if item == "Milk or water":
                item = "Milk"

            if item in ["Milk", "Sugar"]:
                daily_usage[date][item] += amount

    rows = []

    for date, ingredients in daily_usage.items():
        rows.append({
            "date": date,
            "Milk": ingredients.get("Milk", 0),
            "Sugar": ingredients.get("Sugar", 0)
        })

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("No daily ingredient usage could be calculated. Check sales and recipe names.")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Fill missing calendar days with 0 usage.
    # Assumption: days without recorded transactions have no recorded ingredient usage.
    full_dates = pd.date_range(start=df["date"].min(), end=df["date"].max(), freq="D")
    df = df.set_index("date").reindex(full_dates, fill_value=0)
    df.index.name = "date"
    df = df.reset_index()

    return df


def create_future_plot(df, ingredient, alpha, horizon):
    values = df[ingredient].tolist()
    future_values = forecast_future(values, alpha, horizon)

    last_date = df["date"].max()
    future_dates = [
        last_date + timedelta(days=i)
        for i in range(1, horizon + 1)
    ]

    unit = "ml" if ingredient == "Milk" else "g"

    plt.figure(figsize=(12, 6))
    plt.plot(df["date"], values, label="Original data")
    plt.plot(future_dates, future_values, label="Forecasted future data", marker="o")

    plt.title(f"{ingredient} usage forecast with Single Exponential Smoothing, alpha = {alpha}")
    plt.xlabel("Date")
    plt.ylabel(f"{ingredient} usage ({unit})")
    plt.legend()
    plt.tight_layout()

    filename = f"future_forecast_{ingredient.lower()}.png"
    plt.savefig(filename)
    plt.close()

    print("Created:", filename)


def create_evaluation_plot(df, ingredient, alpha):
    values = df[ingredient].tolist()
    dates = df["date"].tolist()

    split_index = int(len(values) * 0.8)

    train_values = values[:split_index]
    test_values = values[split_index:]

    train_dates = dates[:split_index]
    test_dates = dates[split_index:]

    forecasted_test_values = rolling_evaluation_forecast(
        train_values,
        test_values,
        alpha
    )

    unit = "ml" if ingredient == "Milk" else "g"

    plt.figure(figsize=(12, 6))
    plt.plot(train_dates, train_values, label="Training data")
    plt.plot(test_dates, test_values, label="Actual test data")
    plt.plot(test_dates, forecasted_test_values, label="Forecasted test data", marker="o")

    plt.title(f"Evaluation forecast for {ingredient}, Single Exponential Smoothing, alpha = {alpha}")
    plt.xlabel("Date")
    plt.ylabel(f"{ingredient} usage ({unit})")
    plt.legend()
    plt.tight_layout()

    filename = f"evaluation_forecast_{ingredient.lower()}.png"
    plt.savefig(filename)
    plt.close()

    print("Created:", filename)


def main():
    df = load_daily_ingredient_usage()

    print("\nAvailable ingredients:")
    print("1. Milk")
    print("2. Sugar")

    choice = input("Choose ingredient, enter 1 or 2: ")

    if choice == "1":
        ingredient = "Milk"
    elif choice == "2":
        ingredient = "Sugar"
    else:
        print("Invalid choice. Defaulting to Milk.")
        ingredient = "Milk"

    alpha = float(input("Enter alpha between 0 and 1, for example 0.7: "))
    horizon = int(input("Enter forecast horizon in days, for example 7: "))

    if alpha <= 0 or alpha > 1:
        raise ValueError("Alpha must be greater than 0 and less than or equal to 1.")

    create_future_plot(df, ingredient, alpha, horizon)
    create_evaluation_plot(df, ingredient, alpha)

    print("\nDone.")
    print("The plots were generated automatically.")


if __name__ == "__main__":
    main()
