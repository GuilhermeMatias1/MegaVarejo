import sys
import db

class DatabaseConnection:
    """
    Classe gerenciadora de conexões com o banco de dados MySQL.
    Encapsula os detalhes de configuração, parsing de URLs (Render/Railway), SSL e timeouts.
    Delega para a função get_db_connection do app (se já carregado e interceptado em testes) ou de db.
    """

    @classmethod
    def get_connection(cls):
        # Permite que @patch('app.get_db_connection') intercepte se app estiver no sys.modules
        if 'app' in sys.modules and hasattr(sys.modules['app'], 'get_db_connection'):
            return sys.modules['app'].get_db_connection()
        return db.get_db_connection()

