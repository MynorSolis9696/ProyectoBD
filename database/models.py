from datetime import datetime
from database.oracle_connection import OracleConnection
import hashlib
import secrets

class Usuario:
    def __init__(self, id=None, nombre=None, email=None, password_hash=None, rol=None, fecha_registro=None):
        self.id = id
        self.nombre = nombre
        self.email = email
        self.password_hash = password_hash
        self.rol = rol
        self.fecha_registro = fecha_registro
    
    @staticmethod
    def hash_password(password):
        salt = secrets.token_hex(16)
        return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex() + ':' + salt
    
    def verify_password(self, password):
        if not self.password_hash or ':' not in self.password_hash:
            return False
        password_hash, salt = self.password_hash.split(':')
        return password_hash == hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    
    @classmethod
    def get_by_email(cls, email):
        db = OracleConnection()
        query = "SELECT * FROM usuarios WHERE email = :email"
        results = db.execute_query(query, {'email': email})
        if results:
            user_data = results[0]
            return cls(**user_data)
        return None
    
    @classmethod
    def get_by_id(cls, user_id):
        db = OracleConnection()
        query = "SELECT * FROM usuarios WHERE id = :id"
        results = db.execute_query(query, {'id': user_id})
        if results:
            user_data = results[0]
            return cls(**user_data)
        return None
    
    @classmethod
    def get_all(cls):
        db = OracleConnection()
        query = "SELECT * FROM usuarios ORDER BY nombre"
        results = db.execute_query(query)
        return [cls(**data) for data in results]
    
    def save(self):
        db = OracleConnection()
        if self.id:
            query = """
                UPDATE usuarios SET nombre = :nombre, email = :email, 
                rol = :rol WHERE id = :id
            """
            params = {
                'nombre': self.nombre,
                'email': self.email,
                'rol': self.rol,
                'id': self.id
            }
        else:
            query = """
                INSERT INTO usuarios (nombre, email, password_hash, rol) 
                VALUES (:nombre, :email, :password_hash, :rol)
            """
            params = {
                'nombre': self.nombre,
                'email': self.email,
                'password_hash': self.password_hash,
                'rol': self.rol
            }
        db.execute_query(query, params, fetch=False)

class Libro:
    def __init__(self, id=None, titulo=None, autor=None, año_publicacion=None, 
                 genero=None, isbn=None, numero_copias=None, copias_disponibles=None, fecha_registro=None):
        self.id = id
        self.titulo = titulo
        self.autor = autor
        self.año_publicacion = año_publicacion
        self.genero = genero
        self.isbn = isbn
        self.numero_copias = numero_copias or 1
        self.copias_disponibles = copias_disponibles or self.numero_copias
        self.fecha_registro = fecha_registro
    
    @classmethod
    def get_all(cls):
        db = OracleConnection()
        query = "SELECT * FROM libros ORDER BY titulo"
        results = db.execute_query(query)
        return [cls(**data) for data in results]
    
    @classmethod
    def get_by_id(cls, libro_id):
        db = OracleConnection()
        query = "SELECT * FROM libros WHERE id = :id"
        results = db.execute_query(query, {'id': libro_id})
        if results:
            return cls(**results[0])
        return None
    
    @classmethod
    def search(cls, termino):
        db = OracleConnection()
        query = """
            SELECT * FROM libros 
            WHERE UPPER(titulo) LIKE UPPER(:termino) 
               OR UPPER(autor) LIKE UPPER(:termino)
               OR UPPER(genero) LIKE UPPER(:termino)
            ORDER BY titulo
        """
        results = db.execute_query(query, {'termino': f'%{termino}%'})
        return [cls(**data) for data in results]
    
    @classmethod
    def get_low_stock(cls, threshold=5):
        db = OracleConnection()
        query = "SELECT * FROM libros WHERE copias_disponibles <= :threshold ORDER BY copias_disponibles"
        results = db.execute_query(query, {'threshold': threshold})
        return [cls(**data) for data in results]
    
    def save(self):
        db = OracleConnection()
        if self.id:
            query = """
                UPDATE libros SET titulo = :titulo, autor = :autor, 
                año_publicacion = :año_publicacion, genero = :genero, isbn = :isbn,
                numero_copias = :numero_copias, copias_disponibles = :copias_disponibles
                WHERE id = :id
            """
            params = {
                'titulo': self.titulo,
                'autor': self.autor,
                'año_publicacion': self.año_publicacion,
                'genero': self.genero,
                'isbn': self.isbn,
                'numero_copias': self.numero_copias,
                'copias_disponibles': self.copias_disponibles,
                'id': self.id
            }
        else:
            query = """
                INSERT INTO libros (titulo, autor, año_publicacion, genero, isbn, numero_copias, copias_disponibles) 
                VALUES (:titulo, :autor, :año_publicacion, :genero, :isbn, :numero_copias, :copias_disponibles)
            """
            params = {
                'titulo': self.titulo,
                'autor': self.autor,
                'año_publicacion': self.año_publicacion,
                'genero': self.genero,
                'isbn': self.isbn,
                'numero_copias': self.numero_copias,
                'copias_disponibles': self.copias_disponibles
            }
        db.execute_query(query, params, fetch=False)
    
    def delete(self):
        db = OracleConnection()
        query = "DELETE FROM libros WHERE id = :id"
        db.execute_query(query, {'id': self.id}, fetch=False)

class Prestamo:
    def __init__(self, id=None, libro_id=None, usuario_id=None, fecha_prestamo=None, 
                 fecha_devolucion=None, estado=None, libro_titulo=None, usuario_nombre=None):
        self.id = id
        self.libro_id = libro_id
        self.usuario_id = usuario_id
        self.fecha_prestamo = fecha_prestamo
        self.fecha_devolucion = fecha_devolucion
        self.estado = estado
        self.libro_titulo = libro_titulo
        self.usuario_nombre = usuario_nombre
    
    @classmethod
    def get_all_active(cls):
        db = OracleConnection()
        query = """
            SELECT p.*, l.titulo as libro_titulo, u.nombre as usuario_nombre
            FROM prestamos p
            JOIN libros l ON p.libro_id = l.id
            JOIN usuarios u ON p.usuario_id = u.id
            WHERE p.estado = 'ACTIVO'
            ORDER BY p.fecha_prestamo DESC
        """
        results = db.execute_query(query)
        prestamos = []
        for data in results:
            prestamo = cls(
                id=data['ID'],
                libro_id=data['LIBRO_ID'],
                usuario_id=data['USUARIO_ID'],
                fecha_prestamo=data['FECHA_PRESTAMO'],
                fecha_devolucion=data['FECHA_DEVOLUCION'],
                estado=data['ESTADO'],
                libro_titulo=data['LIBRO_TITULO'],
                usuario_nombre=data['USUARIO_NOMBRE']
            )
            prestamos.append(prestamo)
        return prestamos
    
    @classmethod
    def create(cls, libro_id, usuario_id):
        db = OracleConnection()
        
        # Verificar disponibilidad
        libro = Libro.get_by_id(libro_id)
        if not libro or libro.copias_disponibles <= 0:
            raise Exception("Libro no disponible para préstamo")
        
        # Crear préstamo
        query = """
            INSERT INTO prestamos (libro_id, usuario_id) 
            VALUES (:libro_id, :usuario_id)
        """
        db.execute_query(query, {'libro_id': libro_id, 'usuario_id': usuario_id}, fetch=False)
        
        # Actualizar copias disponibles
        update_query = """
            UPDATE libros SET copias_disponibles = copias_disponibles - 1 
            WHERE id = :libro_id
        """
        db.execute_query(update_query, {'libro_id': libro_id}, fetch=False)
        
        return True
    
    @classmethod
    def devolver(cls, prestamo_id):
        db = OracleConnection()
        
        # Obtener información del préstamo
        query = "SELECT * FROM prestamos WHERE id = :id"
        results = db.execute_query(query, {'id': prestamo_id})
        if not results:
            raise Exception("Préstamo no encontrado")
        
        prestamo_data = results[0]
        
        # Actualizar préstamo
        update_prestamo = """
            UPDATE prestamos 
            SET estado = 'DEVUELTO', fecha_devolucion = SYSDATE 
            WHERE id = :id
        """
        db.execute_query(update_prestamo, {'id': prestamo_id}, fetch=False)
        
        # Actualizar copias disponibles del libro
        update_libro = """
            UPDATE libros SET copias_disponibles = copias_disponibles + 1 
            WHERE id = :libro_id
        """
        db.execute_query(update_libro, {'libro_id': prestamo_data['LIBRO_ID']}, fetch=False)
        
        return True