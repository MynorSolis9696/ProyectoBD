# myapp.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import check_password_hash
from datetime import timedelta
from functools import wraps
import os, oracledb
from config import Config

# ----------------- App -----------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)                 # SECRET_KEY, ORA_USER, etc.
app.permanent_session_lifetime = timedelta(minutes=30)

# ----------------- DB helpers -----------------
def get_conn():
    return oracledb.connect(
        user=os.getenv("ORA_USER", "SYSTEM"),
        password=os.getenv("ORA_PASS", "12345678"),
        dsn=os.getenv("ORA_DSN", "localhost:1521/XE")
    )

def query_one(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0].lower() for d in cur.description]
            return dict(zip(cols, row))

def query_all(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            rows = cur.fetchall()
            cols = [d[0].lower() for d in cur.description]
            return [dict(zip(cols, r)) for r in rows]

def execute(sql, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
        conn.commit()

def safe_count(sql, params=None):
    """Devuelve 0 si la tabla no existe o hay error.

    Acepta bind params opcionales y las pasa a query_one para consultas seguras.
    """
    try:
        r = query_one(sql, params or {})
        return (r or {}).get("c", 0) or 0
    except Exception:
        app.logger.debug("safe_count fallo para sql=%s params=%s", sql, params)
        return 0

# ----------------- Auth helpers -----------------
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def librarian_only(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Allow both BIBLIOTECARIO and ADMIN roles to perform librarian actions
        if session.get("user_rol") not in ("BIBLIOTECARIO", "ADMIN"):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

# ----------------- Rutas auth -----------------
@app.get("/", endpoint="index")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/login", methods=["GET", "POST"], endpoint="login")
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        password = request.form.get("password","")

        user = query_one("""
            SELECT id, nombre, email, password_hash, rol
            FROM usuarios
            WHERE email = :email
        """, {"email": email})

        if not user:
            flash("Usuario no encontrado", "danger")
            return render_template("login.html")

        # Valida hash (o contraseña de prueba si aún no tienes hash)
        if check_password_hash(user["password_hash"], password) or password == "admin123":
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["nombre"]
            session["user_rol"] = user["rol"]
            session.permanent = True
            return redirect(url_for("dashboard"))
        else:
            flash("Contraseña incorrecta", "danger")

    return render_template("login.html")

@app.get("/logout", endpoint="logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ----------------- Dashboard -----------------
@app.get("/dashboard", endpoint="dashboard")
@login_required
def dashboard():
    tot_usuarios   = safe_count("SELECT COUNT(*) c FROM usuarios")
    tot_libros     = safe_count("SELECT COUNT(*) c FROM libros")
    if session.get("user_rol") in ("BIBLIOTECARIO", "ADMIN"):
        tot_prestamos = safe_count("SELECT COUNT(*) c FROM prestamos WHERE estado='ACTIVO'")
    else:
        try:
            uid = int(session.get("user_id"))
        except Exception:
            uid = session.get("user_id")
        app.logger.debug("dashboard: counting prestamos for user_id=%s", uid)
        tot_prestamos = safe_count("SELECT COUNT(*) c FROM prestamos WHERE estado='ACTIVO' AND usuario_id=:user_id", {"user_id": uid})
    return render_template("dashboard.html",
                           tot_usuarios=tot_usuarios,
                           tot_libros=tot_libros,
                           tot_prestamos=tot_prestamos,
                           usuario=session.get("user_name"))

# ----------------- Libros -----------------
@app.get("/libros", endpoint="libros_listar")
@login_required
def libros_listar():
    libros = query_all("""
        SELECT id, titulo, autor, anio_publicacion, genero, isbn,
               numero_copias, copias_disponibles, fecha_registro
        FROM libros
        ORDER BY titulo
    """)
    return render_template("libros/listar.html", libros=libros)


@app.route("/libros/editar/<int:libro_id>", methods=["GET","POST"], endpoint="libros_editar")
@login_required
@librarian_only
def libros_editar(libro_id):
    libro = query_one("SELECT * FROM libros WHERE id = :id", {"id": libro_id})
    if not libro:
        flash("Libro no encontrado", "warning")
        return redirect(url_for("libros_listar"))

    if request.method == "POST":
        data = {
            "id": libro_id,
            "titulo": request.form.get("titulo", libro.get("titulo", "")).strip(),
            "autor": request.form.get("autor", libro.get("autor", "")).strip(),
            "anio": int(request.form.get("anio_publicacion") or libro.get("anio_publicacion") or 0),
            "genero": request.form.get("genero", libro.get("genero")),
            "copias": int(request.form.get("numero_copias") or libro.get("numero_copias") or 1),
            "disp": int(request.form.get("copias_disponibles") or libro.get("copias_disponibles") or 0),
        }
        execute("""
            UPDATE libros
            SET titulo = :titulo,
                autor = :autor,
                numero_copias = :copias,
                copias_disponibles = LEAST(:disp, :copias),
                genero = :genero
            WHERE id = :id
        """, data)
        flash("Libro actualizado", "success")
        return redirect(url_for("libros_listar"))

    return render_template("libros/editar.html", libro=libro)


@app.route("/libros/eliminar/<int:libro_id>", methods=["POST"], endpoint="libros_eliminar")
@login_required
@librarian_only
def libros_eliminar(libro_id):
    libro = query_one("SELECT id FROM libros WHERE id = :id", {"id": libro_id})
    if not libro:
        flash("Libro no encontrado", "warning")
        return redirect(url_for("libros_listar"))
    execute("DELETE FROM libros WHERE id = :id", {"id": libro_id})
    flash("Libro eliminado", "success")
    return redirect(url_for("libros_listar"))

@app.route("/libros/agregar", methods=["GET","POST"], endpoint="libros_agregar")
@login_required
@librarian_only
def libros_agregar():
    if request.method == "POST":
        anio = int(request.form.get("anio_publicacion") or 0)
        if anio < 1900:
            flash("No se permite ingresar libros con año menor a 1900", "danger")
            return render_template("libros/agregar.html")
        data = {
            "titulo": request.form["titulo"].strip(),
            "autor": request.form["autor"].strip(),
            "anio": anio,
            "genero": request.form.get("genero"),
            "isbn": request.form.get("isbn"),
            "copias": int(request.form.get("numero_copias") or 0),
            "disp": int(request.form.get("copias_disponibles") or 0),
        }
        execute("""
            INSERT INTO libros (titulo, autor, anio_publicacion, genero, isbn,
                                numero_copias, copias_disponibles)
            VALUES (:titulo, :autor, :anio, :genero, :isbn, :copias, :disp)
        """, data)
        flash("Libro agregado", "success")
        return redirect(url_for("libros_listar"))
    return render_template("libros/agregar.html")

# ----------------- Prestamos -----------------
@app.get("/prestamos", endpoint="prestamos_listar")
@login_required
def prestamos_listar():
    # Librarian/admins see all préstamos; regular users see only theirs
    prestamos_count = None
    if session.get('user_rol') in ('BIBLIOTECARIO', 'ADMIN'):
        # Try to include optional columns (dias, penalizacion); fallback if columns don't exist
        if safe_count("SELECT COUNT(*) c FROM prestamos"):
            try:
                prestamos = query_all("""
                    SELECT p.id, u.nombre AS usuario, l.titulo AS libro, l.editorial AS editorial,
                           p.fecha_prestamo, p.fecha_devolucion, p.dias, p.penalizacion, p.estado
                    FROM prestamos p
                    JOIN usuarios u ON p.usuario_id = u.id
                    JOIN libros l ON p.libro_id = l.id
                    ORDER BY p.id DESC
                """)
            except Exception:
                prestamos = query_all("""
                    SELECT p.id, u.nombre AS usuario, l.titulo AS libro, l.editorial AS editorial,
                           p.fecha_prestamo, p.fecha_devolucion, p.estado
                    FROM prestamos p
                    JOIN usuarios u ON p.usuario_id = u.id
                    JOIN libros l ON p.libro_id = l.id
                    ORDER BY p.id DESC
                """)
        else:
            prestamos = []
        # Para bibliotecario/admin, prestamos_count no se muestra
        prestamos_count = None
    else:
        # Ensure we use a consistent bind name and an int user_id when possible
        try:
            user_id = int(session.get('user_id'))
        except Exception:
            user_id = session.get('user_id')
        app.logger.debug("prestamos_listar: user_id=%s, user_rol=%s", user_id, session.get('user_rol'))
        if safe_count("SELECT COUNT(*) c FROM prestamos"):
            try:
                prestamos = query_all("""
                    SELECT p.id, u.nombre AS usuario, l.titulo AS libro, l.editorial AS editorial,
                           p.fecha_prestamo, p.fecha_devolucion, p.dias, p.penalizacion, p.estado
                    FROM prestamos p
                    JOIN usuarios u ON p.usuario_id = u.id
                    JOIN libros l ON p.libro_id = l.id
                    WHERE p.usuario_id = :user_id
                    ORDER BY p.id DESC
                """, {"user_id": user_id})
            except Exception:
                prestamos = query_all("""
                    SELECT p.id, u.nombre AS usuario, l.titulo AS libro, l.editorial AS editorial,
                           p.fecha_prestamo, p.fecha_devolucion, p.estado
                    FROM prestamos p
                    JOIN usuarios u ON p.usuario_id = u.id
                    JOIN libros l ON p.libro_id = l.id
                    WHERE p.usuario_id = :user_id
                    ORDER BY p.id DESC
                """, {"user_id": user_id})
            # Contar préstamos activos del usuario
            prestamos_count = safe_count("SELECT COUNT(*) c FROM prestamos WHERE usuario_id=:user_id AND estado='ACTIVO'", {"user_id": user_id})
        else:
            prestamos = []
            prestamos_count = 0
    return render_template("prestamos/listar.html", prestamos=prestamos, prestamos_count=prestamos_count)

# NUEVA RUTA — crear préstamo
@app.route("/prestamos/nuevo", methods=["GET", "POST"], endpoint="prestamos_nuevo")
@login_required
def prestamos_nuevo():
    if request.method == "POST":
        # Validate numeric fields
        try:
            usuario_id = int(request.form["usuario_id"])
            libro_id = int(request.form["libro_id"])
        except (KeyError, ValueError):
            flash("Datos de formulario inválidos", "danger")
            return redirect(url_for("prestamos_nuevo"))

        try:
            dias = int(request.form.get("dias") or 14)
            if dias <= 0:
                dias = 14
        except ValueError:
            dias = 14

        penalizacion = '1Q por dia'

        # Check book availability before inserting
        libro = query_one("SELECT id, copias_disponibles FROM libros WHERE id = :id", {"id": libro_id})
        if not libro or int(libro.get("copias_disponibles") or 0) <= 0:
            flash("El libro no está disponible para préstamo", "warning")
            return redirect(url_for("prestamos_nuevo"))

        # Prepare param sets
        base_params = {"usuario_id": usuario_id, "libro_id": libro_id}
        opt_params = {**base_params, "dias": dias, "penalizacion": penalizacion}

        # Try to insert with optional columns; if DB doesn't have them, fallback without extra binds
        inserted = False
        try:
            execute("""
                INSERT INTO prestamos (usuario_id, libro_id, fecha_prestamo, estado, dias, penalizacion)
                VALUES (:usuario_id, :libro_id, SYSDATE, 'ACTIVO', :dias, :penalizacion)
            """, opt_params)
            inserted = True
        except Exception:
            try:
                execute("""
                    INSERT INTO prestamos (usuario_id, libro_id, fecha_prestamo, estado)
                    VALUES (:usuario_id, :libro_id, SYSDATE, 'ACTIVO')
                """, base_params)
                inserted = True
            except Exception as e:
                app.logger.exception("Error al insertar préstamo: %s", e)
                flash("No se pudo registrar el préstamo (error de base de datos)", "danger")
                return redirect(url_for("prestamos_nuevo"))

        # Only decrement copies if insert succeeded
        if inserted:
            try:
                execute("""
                    UPDATE libros
                    SET copias_disponibles = copias_disponibles - 1
                    WHERE id = :libro_id
                """, {"libro_id": libro_id})
            except Exception as e:
                app.logger.exception("Error al actualizar copias: %s", e)
                flash("Préstamo registrado pero no se pudo actualizar el inventario", "warning")
                return redirect(url_for("prestamos_listar"))

        flash("Préstamo registrado correctamente", "success")
        return redirect(url_for("prestamos_listar"))

    usuarios = query_all("SELECT id, nombre FROM usuarios ORDER BY nombre")
    libros = query_all("SELECT id, titulo, editorial FROM libros WHERE copias_disponibles > 0 ORDER BY titulo")
    return render_template("prestamos/nuevo.html", usuarios=usuarios, libros=libros)


@app.route("/prestamos/devolver/<int:prestamo_id>", methods=["POST"], endpoint="prestamos_devolver")
@login_required
@librarian_only
def prestamos_devolver(prestamo_id):
    # Verificar que el préstamo exista y esté activo
    prestamo = query_one("SELECT id, libro_id, estado FROM prestamos WHERE id = :id", {"id": prestamo_id})
    if not prestamo:
        flash("Préstamo no encontrado", "warning")
        return redirect(url_for("prestamos_listar"))

    if prestamo.get("estado") != "ACTIVO":
        flash("El préstamo ya fue devuelto", "info")
        return redirect(url_for("prestamos_listar"))

    # Marcar como devuelto y actualizar copias
    execute("""
        UPDATE prestamos
        SET estado = 'DEVUELTO', fecha_devolucion = SYSDATE
        WHERE id = :id
    """, {"id": prestamo_id})

    execute("""
        UPDATE libros
        SET copias_disponibles = copias_disponibles + 1
        WHERE id = :libro_id
    """, {"libro_id": prestamo.get("libro_id")})

    flash("Préstamo marcado como devuelto", "success")
    return redirect(url_for("prestamos_listar"))
# ----------------- Reportes -----------------
@app.get("/reportes/bajo_stock", endpoint="reporte_bajo_stock")
@login_required
def reporte_bajo_stock():
    # Permitir ajustar el umbral desde querystring: ?threshold=3
    try:
        threshold = int(request.args.get('threshold', 2))
    except ValueError:
        threshold = 2

    libros = []
    if safe_count("SELECT COUNT(*) c FROM libros"):
        libros = query_all(
            """
            SELECT id, titulo, autor, copias_disponibles
            FROM libros
            WHERE copias_disponibles <= :threshold
            ORDER BY copias_disponibles ASC, titulo
            """,
            {"threshold": threshold}
        )

    return render_template("reportes/bajo_stock.html", libros=libros, threshold=threshold)


@app.get('/reportes/bajo_stock/download', endpoint='reporte_bajo_stock_download')
@login_required
def reporte_bajo_stock_download():
    """Download low-stock books as CSV. Accepts ?threshold=NUMBER"""
    try:
        threshold = int(request.args.get('threshold', 2))
    except ValueError:
        threshold = 2

    # Fetch rows
    rows = query_all(
        "SELECT id, titulo, autor, numero_copias, copias_disponibles FROM libros WHERE copias_disponibles <= :threshold ORDER BY copias_disponibles ASC, titulo",
        {"threshold": threshold}
    ) if safe_count("SELECT COUNT(*) c FROM libros") else []

    # Build CSV
    from io import StringIO
    import csv
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["id", "titulo", "autor", "numero_copias", "copias_disponibles"])
    for r in rows:
        writer.writerow([r.get('id'), r.get('titulo'), r.get('autor'), r.get('numero_copias'), r.get('copias_disponibles')])

    output = si.getvalue()
    from flask import Response
    headers = {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': f'attachment; filename=low_stock_threshold_{threshold}.csv'
    }
    return Response(output, headers=headers)

# ----------------- Fin -----------------
# Ejecuta:
# python -m flask --app myapp:app run --debug -p 5050
