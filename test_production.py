import os
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class TestProductionConfig(unittest.TestCase):

    @patch('pymysql.connect')
    def test_database_url_parsing(self, mock_connect):
        """Testa se DATABASE_URL (padrão Railway/Render) é interpretada corretamente."""
        import sys
        sys.path.insert(0, BASE_DIR)
        from db import get_db_connection

        fake_url = "mysql://megavarejo_admin:segredo123@containers-us-west.railway.app:6543/erp_prod"
        with patch.dict(os.environ, {'DATABASE_URL': fake_url}, clear=True):
            get_db_connection()

            mock_connect.assert_called_once()
            kwargs = mock_connect.call_args[1]
            self.assertEqual(kwargs['host'], 'containers-us-west.railway.app')
            self.assertEqual(kwargs['port'], 6543)
            self.assertEqual(kwargs['user'], 'megavarejo_admin')
            self.assertEqual(kwargs['password'], 'segredo123')
            self.assertEqual(kwargs['database'], 'erp_prod')

    @patch('pymysql.connect')
    def test_individual_env_vars(self, mock_connect):
        """Testa se as variáveis individuais (Render/VPS) são respeitadas."""
        import sys
        sys.path.insert(0, BASE_DIR)
        from db import get_db_connection

        env_vars = {
            'MYSQL_HOST': 'db.external.host.com',
            'MYSQL_PORT': '3307',
            'MYSQL_USER': 'cloud_user',
            'MYSQL_PASSWORD': 'cloud_password',
            'MYSQL_DATABASE': 'cloud_db',
            'MYSQL_SSL': 'true'
        }
        with patch.dict(os.environ, env_vars, clear=True):
            get_db_connection()

            mock_connect.assert_called_once()
            kwargs = mock_connect.call_args[1]
            self.assertEqual(kwargs['host'], 'db.external.host.com')
            self.assertEqual(kwargs['port'], 3307)
            self.assertEqual(kwargs['user'], 'cloud_user')
            self.assertEqual(kwargs['password'], 'cloud_password')
            self.assertEqual(kwargs['database'], 'cloud_db')
            self.assertIsNotNone(kwargs['ssl'])

    def test_gunicorn_command_procfile(self):
        """Valida a integridade do Procfile."""
        procfile_path = os.path.join(BASE_DIR, 'Procfile')
        with open(procfile_path, 'r', encoding='utf-8') as f:
            procfile_content = f.read()
        self.assertIn('gunicorn', procfile_content)
        self.assertIn('app:app', procfile_content)

    def test_gitignore_protects_env(self):
        """Garante que .env está no .gitignore para segurança de credenciais."""
        gitignore_path = os.path.join(BASE_DIR, '.gitignore')
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            gitignore_content = f.read()
        self.assertIn('.env', gitignore_content)

if __name__ == '__main__':
    unittest.main()
