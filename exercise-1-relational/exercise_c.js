require("dotenv").config();
const { Client } = require("pg");
const fs = require("fs");
const path = require("path");

const client = new Client({
  host: process.env.PGHOST,
  database: process.env.PGDATABASE_C,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  port: process.env.PGPORT,
});

async function main() {
  // iii
  await client.connect();
  console.log("Connected to database");

  // iv
  await client.query(`
    CREATE TABLE IF NOT EXISTS coffee_sales (
      id SERIAL PRIMARY KEY,
      hour_of_day INT NOT NULL,
      cash_type TEXT NOT NULL CHECK (cash_type IN ('card', 'cash')),
      money NUMERIC NOT NULL CHECK (money > 0),
      coffee_name TEXT NOT NULL,
      time_of_day TEXT,
      weekday TEXT,
      month_name TEXT,
      weekdaysort INT,
      monthsort INT,
      date DATE NOT NULL,
      time TIME NOT NULL
    );
  `);
  console.log("Table created");

  const csvPath = path.join(__dirname, "Coffe_sales.csv");
  const lines = fs.readFileSync(csvPath, "utf-8").split("\n");

  console.log("Header:", lines[0]);
  console.log("Row 1:", lines[1]);
  console.log("Row 2:", lines[2]);

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;

    const values = line.split(",");
    await client.query(
      `INSERT INTO coffee_sales (hour_of_day, cash_type, money, coffee_name, time_of_day, weekday, month_name, weekdaysort, monthsort, date, time)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)`,
      [
        values[0],
        values[1],
        values[2],
        values[3],
        values[4],
        values[5],
        values[6],
        values[7],
        values[8],
        values[9],
        values[10],
      ],
    );
  }

  const res = await client.query("SELECT COUNT(*) FROM coffee_sales;");
  console.log("Total rows:", res.rows[0].count);

  const sample = await client.query("SELECT * FROM coffee_sales LIMIT 5;");
  console.table(sample.rows);

  // v
  await client.query(`
    CREATE TABLE coffees (
      id SERIAL PRIMARY KEY,
      coffee_name TEXT NOT NULL UNIQUE
    );
  `);

  await client.query(`
    INSERT INTO coffees (coffee_name)
    SELECT DISTINCT coffee_name FROM coffee_sales;
  `);

  await client.query(`
    ALTER TABLE coffee_sales
    ADD COLUMN coffee_id INT REFERENCES coffees(id);
  `);

  await client.query(`
    UPDATE coffee_sales
    SET coffee_id = coffees.id
    FROM coffees
    WHERE coffee_sales.coffee_name = coffees.coffee_name;
  `);

  await client.query(`
    ALTER TABLE coffee_sales DROP COLUMN coffee_name;
  `);

  const sales = await client.query("SELECT * FROM coffee_sales LIMIT 5;");
  console.table(sales.rows);

  const coffees = await client.query("SELECT * FROM coffees;");
  console.table(coffees.rows);

  await client.end();
}

main().catch(console.error);
