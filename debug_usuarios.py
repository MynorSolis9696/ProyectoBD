from myapp import query_all
rows = query_all('SELECT id, nombre, email FROM usuarios ORDER BY id')
for r in rows:
    print(r)
print(f"Total usuarios: {len(rows)}")
