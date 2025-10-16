from myapp import query_all

rows = query_all("SELECT id, usuario_id, estado FROM prestamos ORDER BY id")
for r in rows:
    print(r)
print(f"Total rows: {len(rows)}")
