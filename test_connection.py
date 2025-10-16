import os, oracledb
print(">>> Probando conexión...")
conn = oracledb.connect(
    user=os.getenv("ORA_USER","SYSTEM"),
    password=os.getenv("ORA_PASS","12345678"),
    dsn=os.getenv("ORA_DSN","localhost:1521/XE")
)
with conn.cursor() as cur:
    cur.execute("SELECT 'OK' FROM dual")
    print(cur.fetchone())
conn.close()
