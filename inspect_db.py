import sqlite3
conn = sqlite3.connect(r'data/walmart_sales.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
print("Tables:", tables)
for t in tables:
    cols = [c[1] for c in conn.execute(f"PRAGMA table_info({t[0]});").fetchall()]
    print(f"\n{t[0]}: {cols}")
    row = conn.execute(f"SELECT * FROM {t[0]} LIMIT 2;").fetchall()
    print("Sample:", row)
conn.close()
