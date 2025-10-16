import cx_Oracle
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OracleConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OracleConnection, cls).__new__(cls)
            cls._instance._initialize_connection()
        return cls._instance
    
    def _initialize_connection(self):
        try:
            self.connection = cx_Oracle.connect(
                user=Config.ORACLE_USER,
                password=Config.ORACLE_PASSWORD,
                dsn=Config.ORACLE_DSN,
                encoding="UTF-8"
            )
            logger.info("✅ Conexión a Oracle establecida exitosamente")
        except cx_Oracle.Error as error:
            logger.error(f"❌ Error al conectar con Oracle: {error}")
            raise
    
    def get_connection(self):
        return self.connection
    
    def close_connection(self):
        if hasattr(self, 'connection'):
            self.connection.close()
            logger.info("Conexión a Oracle cerrada")
    
    def execute_query(self, query, params=None, fetch=True):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch:
                if query.strip().upper().startswith('SELECT'):
                    columns = [col[0] for col in cursor.description]
                    results = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in results]
                else:
                    connection.commit()
                    return cursor.rowcount
            else:
                connection.commit()
                return cursor.rowcount
                
        except cx_Oracle.Error as error:
            connection.rollback()
            logger.error(f"Error en consulta: {error}")
            raise
        finally:
            cursor.close()