"""
Testes específicos para verificar a correta formatação de datas
no backend e nas respostas das rotas da API do MegaVarejo ERP.
"""

import unittest
from unittest.mock import patch, MagicMock
import datetime
from app import app, formatar_data_br

class TestFormatacaoDatas(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        self.client = app.test_client()

    def test_helper_formatar_data_br(self):
        """Testa o formatador direto em Python com datetime e date."""
        dt = datetime.datetime(2026, 11, 22, 14, 30, 45)
        self.assertEqual(formatar_data_br(dt, incluir_hora=True), '22/11/2026 14:30')
        self.assertEqual(formatar_data_br(dt, incluir_hora=False), '22/11/2026')

        d = datetime.date(2026, 5, 9)
        self.assertEqual(formatar_data_br(d, incluir_hora=False), '09/05/2026')

        # None ou vazio
        self.assertEqual(formatar_data_br(None), '')

        # String ISO
        self.assertEqual(formatar_data_br('2026-11-22T18:45:00', incluir_hora=True), '22/11/2026 18:45')

    @patch('app.get_db_connection')
    def test_api_pedidos_formato_data(self, mock_db_conn):
        """Verifica se a rota /api/pedidos retorna datas no formato brasileiro DD/MM/AAAA HH:MM."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        dt_teste = datetime.datetime(2026, 11, 22, 15, 45, 0)
        mock_cursor.fetchall.return_value = [
            {'id': 101, 'data_pedido': dt_teste, 'status': 'Concluído', 'valor_total': 350.00}
        ]

        with self.client.session_transaction() as sess:
            sess['usuario_id'] = 1
            sess['usuario_perfil'] = 'Administrador'

        res = self.client.get('/api/pedidos')
        self.assertEqual(res.status_code, 200)
        dados = res.get_json()
        self.assertEqual(len(dados), 1)
        self.assertEqual(dados[0]['data_formatada'], '22/11/2026 15:45')
        self.assertNotIn('%d', dados[0]['data_formatada'])
        self.assertNotIn('%H', dados[0]['data_formatada'])

    @patch('app.get_db_connection')
    def test_api_obter_pedido_detalhe_formato_data(self, mock_db_conn):
        """Verifica se a rota de detalhe /api/pedidos/<id> formata a data do pedido."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        dt_teste = datetime.datetime(2026, 11, 22, 10, 5, 0)
        mock_cursor.fetchone.return_value = {
            'id': 102,
            'data_pedido': dt_teste,
            'status': 'Pendente',
            'valor_total': 120.00
        }
        mock_cursor.fetchall.return_value = []

        with self.client.session_transaction() as sess:
            sess['usuario_id'] = 1
            sess['usuario_perfil'] = 'Administrador'

        res = self.client.get('/api/pedidos/102')
        self.assertEqual(res.status_code, 200)
        pedido = res.get_json()
        self.assertEqual(pedido['data_formatada'], '22/11/2026 10:05')
        self.assertNotIn('%', pedido['data_formatada'])

    @patch('app.get_db_connection')
    def test_api_clientes_formato_data(self, mock_db_conn):
        """Verifica se a rota /api/clientes retorna datas no formato brasileiro DD/MM/AAAA."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        dt_teste = datetime.datetime(2026, 8, 15, 11, 20, 0)
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'nome': 'Cliente Teste', 'email': 'cli@teste.com', 'telefone': '119999', 'cidade': 'SP', 'criado_em': dt_teste}
        ]

        with self.client.session_transaction() as sess:
            sess['usuario_id'] = 1
            sess['usuario_perfil'] = 'Administrador'

        res = self.client.get('/api/clientes')
        self.assertEqual(res.status_code, 200)
        clientes = res.get_json()
        self.assertEqual(clientes[0]['criado_em'], '15/08/2026')
        self.assertNotIn('%', clientes[0]['criado_em'])

    @patch('app.get_db_connection')
    def test_api_usuarios_formato_data(self, mock_db_conn):
        """Verifica se a rota /api/usuarios retorna datas no formato brasileiro DD/MM/AAAA."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        dt_teste = datetime.datetime(2026, 1, 10, 8, 0, 0)
        mock_cursor.fetchall.return_value = [
            {'id': 1, 'nome': 'Admin', 'email': 'admin@teste.com', 'perfil_id': 1, 'perfil_nome': 'Administrador', 'ativo': 1, 'criado_em': dt_teste}
        ]

        with self.client.session_transaction() as sess:
            sess['usuario_id'] = 1
            sess['usuario_perfil'] = 'Administrador'

        res = self.client.get('/api/usuarios')
        self.assertEqual(res.status_code, 200)
        usuarios = res.get_json()
        self.assertEqual(usuarios[0]['criado_em'], '10/01/2026')
        self.assertNotIn('%', usuarios[0]['criado_em'])

if __name__ == '__main__':
    unittest.main()
