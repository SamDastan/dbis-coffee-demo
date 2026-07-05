require("dotenv").config();
const { Client } = require("pg");

const config = {
  host: process.env.PGHOST,
  database: process.env.PGDATABASE_B,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  port: process.env.PGPORT,
};

async function printTable(client, label) {
  const res = await client.query("SELECT * FROM students ORDER BY id;");
  console.log(`Table content (${label}):`);
  if (res.rows.length === 0) {
    console.log("No entries");
  } else {
    console.table(res.rows);
  }
}

async function main() {
  // i) Open connection A
  const clientA = new Client(config);
  await clientA.connect();
  console.log("[a] connection open");

  // ii) Create table and insert first record
  await clientA.query(`
    DROP TABLE IF EXISTS students;
    CREATE TABLE students (
      id   SERIAL PRIMARY KEY,
      name TEXT NOT NULL,
      grade INT
    );
  `);
  await clientA.query(
    "INSERT INTO students (name, grade) VALUES ('Alice', 1);",
  );
  console.log("[a] table created, Alice inserted");

  // iii) Open connection B
  const clientB = new Client(config);
  await clientB.connect();
  console.log("[b] connection open");

  // iv) Start transactions
  await clientA.query("BEGIN;");
  await clientB.query("BEGIN;");
  console.log("[ab] transactions started");

  // v) Connection A: insert a new record
  await clientA.query("INSERT INTO students (name, grade) VALUES ('Bob', 2);");
  console.log("[a] inserted Bob (2)");

  // vi) Connection B: insert a different new record
  await clientB.query(
    "INSERT INTO students (name, grade) VALUES ('Charlie', 3);",
  );
  console.log("[b] inserted Charlie (3)");

  // vii) Check table contents on both connections
  await printTable(clientA, "connection A before commit");
  await printTable(clientB, "connection B before commit");

  // viii) Commit both transactions
  await clientA.query("COMMIT;");
  console.log("[a] committed");
  await printTable(clientA, "connection A after commit");

  await clientB.query("COMMIT;");
  console.log("[b] committed");
  await printTable(clientB, "connection B after commit");

  // ix) Open a third connection and check contents
  const clientC = new Client(config);
  await clientC.connect();
  await printTable(clientC, "connection C (new)");
  await clientC.end();

  // x) Start new transactions
  await clientA.query("BEGIN;");
  await clientB.query("BEGIN;");
  console.log("[ab] new transactions started");

  // xi) Both update the same record (Alice) with different values
  await clientA.query("UPDATE students SET grade = 10 WHERE name = 'Alice';");
  console.log("[a] Alice grade -> 10");

  console.log("[b] attempting to set Alice grade -> 20");
  try {
    // clientB blocks here until A commits, or until it times out
    await clientB.query("UPDATE students SET grade = 20 WHERE name = 'Alice';");
    console.log("[b] Alice grade -> 20");
  } catch (err) {
    console.log("[b] update failed:", err.message);
  }

  // xii) Commit both
  try {
    await clientA.query("COMMIT;");
    console.log("[a] committed");
    await printTable(clientA, "connection A after update commit");
  } catch (err) {
    console.log("[a] commit failed:", err.message);
    await clientA.query("ROLLBACK;");
  }

  try {
    await clientB.query("COMMIT;");
    console.log("[b] committed");
    await printTable(clientB, "connection B after update commit");
  } catch (err) {
    console.log("[b] commit failed:", err.message);
    await clientB.query("ROLLBACK;");
  }

  // xiii) Third connection: check final result
  const clientD = new Client(config);
  await clientD.connect();
  await printTable(clientD, "connection C (new, after all updates)");
  await clientD.end();

  // Close connections
  await clientA.end();
  await clientB.end();
  console.log("[done]");
}

main().catch((err) => {
  console.error("error:", err);
  process.exit(1);
});
