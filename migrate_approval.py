"""
migrate_approval.py
────────────────────
One-time migration: adds  is_approved  and  pending_role  columns to the
existing  users  table without touching any other data.

Run ONCE from the project root:
    python migrate_approval.py

Safe to run multiple times — it skips columns that already exist.
"""

import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "database.db")


def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    added = []

    if not column_exists(cur, "users", "is_approved"):
        # All existing users are already active → default TRUE (1)
        cur.execute("ALTER TABLE users ADD COLUMN is_approved INTEGER NOT NULL DEFAULT 1")
        added.append("is_approved")

    if not column_exists(cur, "users", "pending_role"):
        cur.execute("ALTER TABLE users ADD COLUMN pending_role VARCHAR(20)")
        added.append("pending_role")

    conn.commit()
    conn.close()

    if added:
        print(f"✅  Migration complete. Added columns: {', '.join(added)}")
    else:
        print("ℹ️   Nothing to migrate — columns already exist.")


if __name__ == "__main__":
    migrate()
