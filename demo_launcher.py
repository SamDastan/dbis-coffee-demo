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

        # Plot 1: Evaluation
        split = int(len(y) * 0.8)
        ax1.plot(dates[split:], y[split:], label="Actual", color='green')
        ax1.plot(dates[split:], smoothed[split-1:-1], label="Prediction", color='orange', ls='--')
        ax1.set_title(f"{ingredient} Evaluation (Alpha {alpha})")
        ax1.set_ylabel(f"{ingredient} usage ({unit})")
        ax1.legend()

        # Plot 2: Future
        future_dates = pd.date_range(dates.iloc[-1], periods=horizon + 1)[1:]
        ax2.plot(dates[-30:], y[-30:], label="Recent History", color='blue') # Show last 30 days for clarity
        ax2.plot(future_dates, [forecast_val] * horizon, color='red', marker='o', label=f'{horizon}-Day Forecast')

        # Add numerical label to plot
        ax2.text(future_dates[0], forecast_val, f'  {forecast_val:.1f} {unit}', color='red', fontweight='bold')

        ax2.set_title(f"{ingredient} Future Demand Plot")
        ax2.set_ylabel(f"{ingredient} usage ({unit})")
        ax2.legend()
        plt.show()

        again = input(f"{YELLOW}Run another forecast? (y/n): {RESET}").strip().lower()
        print()
        if again != "y":
            print(f"{BOLD}{CYAN}Thanks for trying the forecast playground!{RESET}")
            break
    """
    with open('demo.py', 'w') as f:
        f.write(demo_code.strip())

    print("[setup] done, run 'python3 demo.py'")
