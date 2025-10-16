from myapp import query_one, safe_count

user_id = 2
q = "SELECT COUNT(*) c FROM prestamos WHERE usuario_id=:user_id AND estado='ACTIVO'"
print('query_one result:', query_one(q, {'user_id': user_id}))
print('safe_count result:', safe_count(q, {'user_id': user_id}))

# Also test without params
q2 = "SELECT COUNT(*) c FROM prestamos WHERE estado='ACTIVO'"
print('query_one all result:', query_one(q2))
print('safe_count all result:', safe_count(q2))
