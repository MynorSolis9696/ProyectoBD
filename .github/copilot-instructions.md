## Quick orientation

- Entry point: `myapp.py` — a small Flask app that defines routes, simple DB helpers (see `query_one`, `query_all`, `execute`) and basic auth/session handling.
- DB layer: two different approaches exist:
  - `database/oracle_connection.py` implements a singleton `OracleConnection` class using `cx_Oracle` and exposes `execute_query` that returns lists of dicts (column names come through as declared by the driver, often UPPERCASE).
  - `myapp.py` uses `oracledb.connect(...)` directly and its helper functions lowercase column names (see `cols = [d[0].lower() for d in cur.description]`).
- Models: `database/models.py` contains ORM-like classes (`Usuario`, `Libro`, `Prestamo`) which use `OracleConnection` to run SQL and return model instances.
- Templates live under `templates/` with subfolders (e.g. `templates/libros/*`) and static assets under `static/`.

## Important patterns & conventions (concrete, discoverable)

- SQL style: inline SQL strings with named bind parameters (`:param`) are used across the codebase — follow existing binding style.
- Parameter keys come from HTML forms. Example: `myapp.py` expects `request.form['titulo']`, `['autor']`, `['numero_copias']` when adding a book (see route `/libros/agregar`).
- Session/auth: logged-in user data is stored in Flask `session` keys `user_id`, `user_name`, `user_rol`. Protect routes by checking `if "user_id" not in session` as shown.
- Password hashing: `database/models.py` implements a custom PBKDF2+salt scheme (hash + ':' + salt). However, `myapp.py` uses `werkzeug.security.check_password_hash` and also contains a temporary plaintext backdoor password `admin123`. These two are inconsistent — treat this as a high-priority area to standardize before modifying auth behavior.
- Column name casing: model methods and `OracleConnection` return dicts where column names may be uppercase (e.g. `'ID'`, `'LIBRO_ID'`) while `myapp.py`'s helpers return lowercase keys. When editing or introducing code that touches both layers, normalize key casing explicitly or call the appropriate helper.

## Run / developer workflow (PowerShell examples)

1) Create a virtual environment and install deps:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Set required environment variables (or create a `.env` file). Minimal vars used by the app:

```powershell
set ORA_USER=SYSTEM
set ORA_PASS=your_db_password
set ORA_DSN=localhost:1521/XE
set SECRET_KEY=change-me
```

3) Test DB connectivity:

```powershell
python test_connection.py
```

4) Run the app (two options):

```powershell
flask --app myapp --debug run

# or equivalently
python -m flask --app myapp run --debug
```

Notes: `database/oracle_connection.py` imports `cx_Oracle` while `requirements.txt` lists `oracledb`. The environment must satisfy whichever driver you standardize on (see "Driver inconsistency" below).

## Integration points & external dependencies

- Oracle DB: the project relies on Oracle. Ensure the runtime has the correct Oracle driver and any required client libraries.
- Python packages are declared in `requirements.txt` (Flask, oracledb, python-dotenv, Werkzeug). If you switch to `cx_Oracle` you must add/install it explicitly.

## Known issues & gotchas for contributors (actionable)

- Driver inconsistency: `oracledb` vs `cx_Oracle`. `requirements.txt` has `oracledb==3.4.0` but `database/oracle_connection.py` imports `cx_Oracle`. Before editing DB code, standardize on one driver (recommendation: migrate `oracle_connection.py` to use `oracledb` for consistency with `requirements.txt`, or add `cx_Oracle` to requirements and install the Oracle client if needed).
- Auth mismatch: `models.Usuario.hash_password` uses PBKDF2 with a custom format (`hash:salt`) while `myapp.py` calls `werkzeug.security.check_password_hash`. This will cause login failures or silent security issues. Either convert `models` to use Werkzeug's `generate_password_hash`/`check_password_hash` or change `myapp` to verify using the model's `verify_password` logic.
- Temporary backdoor: `myapp.py` accepts password `admin123` for testing. Treat as insecure and remove it for production.
- Column name / field name inconsistencies: `año_publicacion` vs `anio_publicacion` appears in different files. Use caution when accessing these fields across modules.

## Files to open first (helpful entry points)

- `myapp.py` — routes, small DB helpers, and auth flow.
- `database/oracle_connection.py` — singleton DB connection and `execute_query` implementation.
- `database/models.py` — data access patterns, model methods and password hashing logic.
- `config.py` and `test_connection.py` — environment variables and a quick connectivity test.

If any section is unclear or you want me to standardize the DB driver and fix auth/keys as a follow-up, tell me which area to prioritize.
