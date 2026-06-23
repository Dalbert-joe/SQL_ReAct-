"""
database.py – Sets up a SQLite database with sample tables for demo purposes.
Run once: python database.py
"""
import sqlite3
import os

DB_PATH = os.getenv("DATABASE_URL", "database.db").replace("sqlite:///./", "")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            dept     TEXT    NOT NULL,
            salary   REAL    NOT NULL,
            hire_date TEXT   NOT NULL
        );

        CREATE TABLE IF NOT EXISTS departments (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            name   TEXT NOT NULL,
            budget REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            dept_id     INTEGER REFERENCES departments(id),
            start_date  TEXT NOT NULL,
            status      TEXT NOT NULL
        );
    """)

    # Seed only if empty
    if cur.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO employees (name, dept, salary, hire_date) VALUES (?,?,?,?)",
            [
                ("Alice Chen",    "Engineering", 120000, "2020-03-15"),
                ("Bob Patel",     "Engineering", 105000, "2021-07-01"),
                ("Carol Smith",   "Marketing",    88000, "2019-11-20"),
                ("David Kim",     "Engineering", 132000, "2018-06-10"),
                ("Eva Torres",    "HR",           75000, "2022-01-05"),
                ("Frank Nguyen",  "Marketing",    92000, "2020-09-14"),
                ("Grace Liu",     "Finance",      98000, "2021-03-22"),
                ("Hank Brown",    "HR",           72000, "2023-02-18"),
                ("Irene Patel",   "Finance",     115000, "2019-08-30"),
                ("James Wilson",  "Engineering", 143000, "2017-05-12"),
            ]
        )
        cur.executemany(
            "INSERT INTO departments (name, budget) VALUES (?,?)",
            [
                ("Engineering", 5000000),
                ("Marketing",   2000000),
                ("HR",          1000000),
                ("Finance",     1500000),
            ]
        )
        cur.executemany(
            "INSERT INTO projects (title, dept_id, start_date, status) VALUES (?,?,?,?)",
            [
                ("Platform Rewrite",   1, "2024-01-10", "active"),
                ("Brand Refresh",      2, "2024-03-01", "active"),
                ("HRIS Migration",     3, "2024-02-15", "completed"),
                ("Budget Automation",  4, "2024-04-20", "active"),
                ("API Gateway",        1, "2023-11-01", "completed"),
            ]
        )

    conn.commit()
    conn.close()
    print(f"Database initialised at: {DB_PATH}")


if __name__ == "__main__":
    init_db()
