import sqlite3

DB_NAME = "users.db"  # Name of your SQLite database

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # To get dict-like access to rows
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Example table creation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()
    print("Database initialized successfully.")