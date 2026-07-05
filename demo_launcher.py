import subprocess
import sys
import os
import json

# --- 1. Fix Environment ---
def bootstrap():
    print("[setup] installing packages")
    packages = ["numpy", "pandas", "matplotlib", "tinydb", "psycopg2-binary"]
    for package in packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", "--no-cache-dir", package])

if __name__ == "__main__":
    bootstrap()
    import pandas as pd
    import psycopg2
    from psycopg2 import sql
    from tinydb import TinyDB

    PGHOST = os.environ.get("PGHOST", "localhost")
    PGUSER = os.environ.get("PGUSER", "postgres")
    PGPASSWORD = os.environ.get("PGPASSWORD", "")
    PGPORT = os.environ.get("PGPORT", "5432")
    PGDATABASE = os.environ.get("PGDATABASE", "coffee_forecasting")

    print("[setup] checking database exists")
    # Connect to the default 'postgres' database first, since the target
    # database may not exist yet on a fresh PostgreSQL install.
    admin_conn = psycopg2.connect(
        dbname="postgres", user=PGUSER, password=PGPASSWORD, host=PGHOST, port=PGPORT,
    )
    admin_conn.autocommit = True
    admin_cur = admin_conn.cursor()
    admin_cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (PGDATABASE,))
    if admin_cur.fetchone() is None:
        admin_cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(PGDATABASE)))
        print(f"[setup] created database '{PGDATABASE}'")
    admin_cur.close()
    admin_conn.close()

    print("[setup] connecting to postgres")
    # Connection settings can be overridden with environment variables,
    # so this runs on whoever's machine is presenting without editing code.
    conn = psycopg2.connect(
        dbname=PGDATABASE,
        user=PGUSER,
        password=PGPASSWORD,
        host=PGHOST,
        port=PGPORT,
    )
    cur = conn.cursor()

    print("[setup] loading sales into postgres")
    cur.execute("DROP TABLE IF EXISTS sales")
    cur.execute("""
        CREATE TABLE sales (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            time TIME,
            coffee_name TEXT NOT NULL,
            money NUMERIC,
            cash_type TEXT
        )
    """)
    sales_df = pd.read_csv('Coffe_sales.csv')
    for _, row in sales_df.iterrows():
        cur.execute(
            "INSERT INTO sales (date, time, coffee_name, money, cash_type) VALUES (%s, %s, %s, %s, %s)",
            (row["Date"], row.get("Time"), row["coffee_name"], row.get("money"), row.get("cash_type", "")),
        )
    conn.commit()

    print("[setup] joining recipe and sales data")
    tdb = TinyDB('coffee_db.json')
    tdb.truncate()
    with open('coffee_recipes.json', 'r') as f:
        tdb.insert_multiple(json.load(f)['recipes'])

    # coffee_recipes.json only contains the original 6 recipes. Espresso and
    # Cappuccino appear in the sales data but were missing from the initial
    # catalog (see update_db.py); they are added here so no sale is silently
    # dropped for lacking a matching recipe.
    tdb.insert_multiple([
        {
            "id": "espresso",
            "name": "Espresso",
            "category": "Espresso",
            "time_minutes": 2,
            "servings": 1,
            "ingredients": [{"item": "Coffee beans", "amount": 18, "unit": "g"}],
            "equipment": ["Espresso machine"],
            "steps": ["Grind beans", "Brew 30ml shot"],
        },
        {
            "id": "cappuccino",
            "name": "Cappuccino",
            "category": "Cappuccino",
            "time_minutes": 6,
            "servings": 1,
            "ingredients": [{"item": "Espresso", "amount": 1, "unit": "shot"}, {"item": "Milk", "amount": 150, "unit": "ml"}],
            "equipment": ["Espresso machine", "Steam wand"],
            "steps": ["Brew espresso", "Steam milk to thick foam", "Pour over espresso"],
        },
    ])

    cur.execute("SELECT coffee_name, date FROM sales ORDER BY date")
    sales = cur.fetchall()
    recipes = {r['name']: r['ingredients'] for r in tdb.all()}

    # Track both Milk and Sugar, matching Exercise 3's requirement of at
    # least two switchable ingredients. "Milk or water" is counted as Milk.
    usage_list = []
    for coffee_name, date in sales:
        for ing in recipes.get(coffee_name, []):
            item = "Milk" if ing['item'] == "Milk or water" else ing['item']
            if item in ("Milk", "Sugar"):
                usage_list.append({"date": str(date), "ingredient": item, "amount": float(ing['amount'])})

    df = pd.DataFrame(usage_list)
    daily = (
        df.pivot_table(index="date", columns="ingredient", values="amount", aggfunc="sum", fill_value=0)
        .reindex(columns=["Milk", "Sugar"], fill_value=0)
    )
    daily.index = pd.to_datetime(daily.index)
    daily = daily.resample('D').asfreq().fillna(0)
    daily.to_csv('usage_prepped.csv')

    cur.close()
    conn.close()

    # --- 3. Generate demo.py ---
    print("[setup] writing demo.py")
    demo_code = """
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
import subprocess

BOLD = "\\033[1m"
RESET = "\\033[0m"
CYAN = "\\033[96m"
GREEN = "\\033[92m"
YELLOW = "\\033[93m"

def run_ses(values, alpha):
    smoothed = [values[0]]
    for i in range(1, len(values)):
        smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[-1])
    return smoothed

if __name__ == "__main__":
    df = pd.read_csv('usage_prepped.csv', parse_dates=['date'])

    print(f"{BOLD}{CYAN}")
    print("=" * 42)
    print("   Coffee Ingredient Forecast Playground")
    print("=" * 42)
    print(f"{RESET}")

    while True:
        print(f"{BOLD}Available ingredients:{RESET} 1) Milk   2) Sugar")
        choice = input(f"{CYAN}Choose ingredient (1 or 2): {RESET}").strip()
        ingredient = "Sugar" if choice == "2" else "Milk"
        unit = "ml" if ingredient == "Milk" else "g"

        y, dates = df[ingredient].values, df['date']

        alpha = float(input(f"{CYAN}Enter Alpha (0.1 - 0.9): {RESET}"))
        horizon = int(input(f"{CYAN}Enter forecast horizon in days (e.g. 7): {RESET}"))

        smoothed = run_ses(y, alpha)
        forecast_val = smoothed[-1]

        print(f"{GREEN}{BOLD}[result]{RESET}{GREEN} forecast: {forecast_val:.2f} {unit} per day{RESET}\\n")

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        plt.subplots_adjust(hspace=0.4)

        # Plot 1: Evaluation (matches main.py's create_evaluation_plot exactly:
        # full training history, actual test data, and the one-step-ahead forecast)
        split = int(len(y) * 0.8)
        train_dates, test_dates = dates[:split], dates[split:]
        train_values, test_values = y[:split], y[split:]
        forecasted_test_values = smoothed[split - 1:-1]

        ax1.plot(train_dates, train_values, label="Training data")
        ax1.plot(test_dates, test_values, label="Actual test data")
        ax1.plot(test_dates, forecasted_test_values, label="Forecasted test data", marker="o")
        ax1.set_title(f"Evaluation forecast for {ingredient}, Single Exponential Smoothing, alpha = {alpha}")
        ax1.set_xlabel("Date")
        ax1.set_ylabel(f"{ingredient} usage ({unit})")
        ax1.legend()

        # Plot 2: Future (matches main.py's create_future_plot exactly:
        # the full original series plus the forecast appended at the end)
        future_dates = pd.date_range(dates.iloc[-1], periods=horizon + 1)[1:]
        future_values = [forecast_val] * horizon

        ax2.plot(dates, y, label="Original data")
        ax2.plot(future_dates, future_values, label="Forecasted future data", marker="o")
        ax2.set_title(f"{ingredient} usage forecast with Single Exponential Smoothing, alpha = {alpha}")
        ax2.set_xlabel("Date")
        ax2.set_ylabel(f"{ingredient} usage ({unit})")
        ax2.legend()

        filename = "coffee_forecast.png"
        plt.savefig(filename)
        plt.close(fig)
        print(f"{CYAN}Saved plot to {filename}{RESET}")

        try:
            if sys.platform == "darwin":
                subprocess.run(["open", filename])
            elif sys.platform.startswith("linux"):
                subprocess.run(["xdg-open", filename])
            else:
                os.startfile(filename)
        except Exception:
            print(f"{YELLOW}Could not open the image automatically. Open {filename} manually.{RESET}")

        again = input(f"{YELLOW}Run another forecast? (y/n): {RESET}").strip().lower()
        print()
        if again != "y":
            print(f"{BOLD}{CYAN}Thanks for trying the forecast playground!{RESET}")
            break
    """
    with open('demo.py', 'w') as f:
        f.write(demo_code.strip())

    print("[setup] done, run 'python3 demo.py'")
