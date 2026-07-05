# Coffee Shop Ingredient Demand Forecasting

A small end-to-end system that predicts daily coffee-shop ingredient demand (milk and sugar) from historical sales, built for the Databases and Information Systems course (2026) at Universität Hamburg.

The project combines two different database paradigms and a self-implemented forecasting algorithm:

- **PostgreSQL** (relational) stores individual sales transactions
- **TinyDB** (NoSQL, document-based) stores the recipe catalog
- A Python pipeline joins the two to compute daily ingredient usage, then forecasts future demand with **Single Exponential Smoothing (SES)**, implemented from scratch

## Authors

Nousha Allahyari, Kaja Zabinski, Paul Maurer

## How the pieces fit together

```
Recipe Catalog (JSON)  ──▶  TinyDB (documents)  ──┐
                                                    ├──▶  Join (Python)  ──▶  Daily usage  ──▶  SES forecast  ──▶  Plots
Sales Log (CSV)         ──▶  PostgreSQL (rows)  ──┘
```

Each sale is matched to its recipe to compute how much milk and sugar it required; days without sales are filled with zero usage so the resulting series has no gaps. The forecast is evaluated on held-out data (80/20 split) and used to project demand for future days.

## What each exercise contributed

| Exercise | Focus | Key files |
|---|---|---|
| 1 | Relational database: setup, concurrent transactions, CSV import with constraints, normalization (FK) | `exercise-1-relational/exercise_b.js`, `exercise-1-relational/exercise_c.js` |
| 2 | NoSQL database: recipe storage, API queries, joining with relational data, aggregation | `exercise-2-nosql/query_task.py`, `exercise-2-nosql/update_db.py`, `exercise-2-nosql/aggregation_task.py` |
| 3 | Forecasting: self-implemented SES, CLI, adjustable parameters, evaluation on real data | `exercise-3-forecasting/forecasting.py`, `exercise-3-forecasting/main.py`, `exercise-3-forecasting/setup_sales_postgres.py` |

Exercise 1's transaction test and FK normalization proved PostgreSQL's relational properties for that exercise, but the live demo below uses a simpler single `sales` table for speed and portability — the underlying database engine (PostgreSQL) stays the same throughout.

## Running the demo

The demo is consolidated into two scripts so it can be run with minimal setup on any machine.

**Requirements:** Python 3, PostgreSQL running locally (or reachable), and the packages listed below (installed automatically by the launcher).

**1. Set your PostgreSQL connection** (only needed if it differs from the defaults: `localhost`, user `postgres`, empty password, port `5432`, database `coffee_forecasting`):

```bash
export PGHOST=localhost
export PGUSER=your_user
export PGPASSWORD=your_password
export PGDATABASE=coffee_forecasting
export PGPORT=5432
```

**2. Run the launcher.** This installs dependencies, loads `Coffe_sales.csv` into PostgreSQL, loads `coffee_recipes.json` into TinyDB, joins both into a daily usage table, and generates `demo.py`:

```bash
python3 demo_launcher.py
```

**3. Run the interactive demo:**

```bash
python3 demo.py
```

You'll be asked to pick an ingredient (milk or sugar) and a smoothing factor (alpha, between 0.1 and 0.9). The script then shows two plots: an evaluation forecast against held-out historical data, and a 7-day forecast into the future.

## Project structure

```
dbis-coffee-demo/
├── README.md
├── demo_launcher.py            # Sets up databases, joins data, generates demo.py
├── coffee_recipes.json         # Recipe catalog (source data)
├── Coffe_sales.csv             # Sales transaction log (source data)
├── exercise-1-relational/
│   ├── exercise_b.js            # Concurrent transactions test
│   ├── exercise_c.js            # CSV import with constraints + normalization
│   ├── package.json
│   ├── .env.example
│   └── .gitignore
├── exercise-2-nosql/
│   ├── query_task.py            # TinyDB API query example
│   ├── update_db.py             # Adds recipes missing from the initial catalog
│   ├── aggregation_task.py      # Joins TinyDB + CSV to aggregate prep time per day
│   ├── setup_db.py              # Loads recipes into TinyDB
│   └── coffee_db.json           # Generated TinyDB file
└── exercise-3-forecasting/
    ├── forecasting.py            # Self-implemented SES (upload requirement: forecasting logic only)
    ├── main.py                   # Original per-exercise pipeline: join + CLI + plotting
    ├── setup_sales_postgres.py   # Loads sales CSV into PostgreSQL
    ├── info.txt                  # Forecasting algorithm, parameters, and assumptions
    ├── evaluation_forecast_milk.png
    └── future_forecast_milk.png
```

## Assumptions

- The recipe "Cocoa" lists the ingredient choice "Milk or water"; this is treated as **Milk** throughout.
- Only Milk and Sugar are tracked for forecasting, since these are the ingredients shared across multiple recipes and explicitly required by Exercise 3.
- Calendar days with no recorded sale are assigned zero ingredient usage rather than omitted, so the daily time series has no gaps.
