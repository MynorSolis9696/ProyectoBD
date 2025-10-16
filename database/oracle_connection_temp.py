import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OracleConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OracleConnection, cls).__new__(cls)
        return cls._instance
    
    def execute_query(self, query, params=None, fetch=True):
        # Simular datos para pruebas sin Oracle
        logger.info("⚠️  MODO SIMULACIÓN: Sin conexión real a Oracle")
        
        if "usuarios" in query.lower():
            return [
                {'ID': 1, 'NOMBRE': 'Administrador Principal', 'EMAIL': 'admin@biblioteca.com', 'ROL': 'BIBLIOTECARIO'},
                {'ID': 2, 'NOMBRE': 'Juan Pérez', 'EMAIL': 'juan@biblioteca.com', 'ROL': 'LECTOR'}
            ]
        elif "libros" in query.lower():
            return [
                {'ID': 1, 'TITULO': 'Cien años de soledad', 'AUTOR': 'Gabriel García Márquez', 'AÑO_PUBLICACION': 1967}
            ]
        return []