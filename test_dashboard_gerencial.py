import unittest
import datetime
from unittest.mock import MagicMock, patch
from services.dashboard_service import DashboardService
from repositories.dashboard_repository import DashboardRepository
from repositories.financeiro_repository import FinanceiroRepository
from repositories.pedido_repository import PedidoRepository
from repositories.produto_repository import ProdutoRepository
from models.financeiro import ResumoFinanceiro

class TestDashboardGerencial(unittest.TestCase):
    def setUp(self):
        self.mock_dash_repo = MagicMock(spec=DashboardRepository)
        self.mock_fin_repo = MagicMock(spec=FinanceiroRepository)
        self.mock_ped_repo = MagicMock(spec=PedidoRepository)
        self.mock_prod_repo = MagicMock(spec=ProdutoRepository)

        self.service = DashboardService(
            dashboard_repo=self.mock_dash_repo,
            financeiro_repo=self.mock_fin_repo,
            pedido_repo=self.mock_ped_repo,
            produto_repo=self.mock_prod_repo
        )

    def test_calculo_intervalos_e_agrupamentos(self):
        """Valida que o serviço calcula corretamente datas e períodos comparativos equivalentes."""
        hoje = datetime.date.today()

        # 1. 7 dias
        ini, fim, ini_ant, fim_ant, agrup = self.service._resolver_intervalo('7dias')
        self.assertEqual(fim, hoje)
        self.assertEqual((fim - ini).days, 6)
        self.assertEqual((fim_ant - ini_ant).days, 6)
        self.assertEqual(agrup, 'dia')

        # 2. 30 dias
        ini, fim, ini_ant, fim_ant, agrup = self.service._resolver_intervalo('30dias')
        self.assertEqual((fim - ini).days, 29)
        self.assertEqual(agrup, 'dia')

        # 3. Personalizado
        ini, fim, ini_ant, fim_ant, agrup = self.service._resolver_intervalo('personalizado', '2026-01-01', '2026-01-15')
        self.assertEqual(ini, datetime.date(2026, 1, 1))
        self.assertEqual(fim, datetime.date(2026, 1, 15))
        self.assertEqual(agrup, 'dia')

    def test_distincao_entre_faturamento_e_fluxo_caixa(self):
        """
        Garante a regra obrigatória: Faturamento NÃO é confundido com dinheiro recebido no caixa,
        nem contas a receber com saldo disponível em caixa.
        """
        # Mock de dados comerciais
        self.mock_dash_repo.obter_kpis_comerciais.return_value = {
            "faturamento": 50000.00,
            "faturamento_anterior": 40000.00,
            "faturamento_variacao_pct": 25.0,
            "pedidos": 10,
            "ticket_medio": 5000.00
        }

        # Mock de dados financeiros
        mock_resumo_fin = ResumoFinanceiro(
            saldo_disponivel=12500.00,
            total_entradas_caixa=20000.00,
            total_saidas_caixa=7500.00,
            receitas_totais=50000.00,
            despesas_totais=10000.00,
            contas_a_receber=37500.00,
            contas_a_pagar_pendentes=5000.00
        )
        self.mock_fin_repo.obter_resumo_financeiro.return_value = mock_resumo_fin
        self.mock_fin_repo.listar_transacoes_caixa.return_value = [
            {"tipo": "Entrada", "valor": 8000.00},
            {"tipo": "Saída", "valor": 2000.00}
        ]

        self.mock_dash_repo.obter_evolucao_faturamento.return_value = []
        self.mock_dash_repo.obter_distribuicao_status_pedidos.return_value = []
        self.mock_dash_repo.obter_alertas_gerenciais.return_value = {}
        self.mock_dash_repo.obter_pedidos_recentes.return_value = []
        self.mock_dash_repo.obter_produtos_mais_vendidos.return_value = []
        self.mock_dash_repo.obter_entregas_em_andamento.return_value = []
        self.mock_dash_repo.obter_atividades_recentes.return_value = []

        resultado = self.service.obter_metricas(periodo='30dias')

        # Verificações cruciais
        self.assertEqual(resultado['kpis_comerciais']['faturamento'], 50000.00)
        self.assertEqual(resultado['resumo_financeiro']['saldo_disponivel_caixa'], 12500.00)
        self.assertEqual(resultado['resumo_financeiro']['entradas_no_periodo'], 8000.00)
        self.assertEqual(resultado['resumo_financeiro']['saidas_no_periodo'], 2000.00)
        self.assertEqual(resultado['resumo_financeiro']['contas_receber_aberto'], 37500.00)

        # Assegura que faturamento != entradas em caixa
        self.assertNotEqual(resultado['kpis_comerciais']['faturamento'], resultado['resumo_financeiro']['entradas_no_periodo'])
        # Assegura que contas a receber != saldo disponível
        self.assertNotEqual(resultado['resumo_financeiro']['contas_receber_aberto'], resultado['resumo_financeiro']['saldo_disponivel_caixa'])

    def test_alertas_gerenciais_integracao(self):
        """Valida que alertas gerenciais reportam ocorrências reais."""
        self.mock_dash_repo.obter_kpis_comerciais.return_value = {}
        self.mock_fin_repo.obter_resumo_financeiro.return_value = ResumoFinanceiro(0, 0, 0, 0, 0, 0, 0)
        self.mock_fin_repo.listar_transacoes_caixa.return_value = []
        self.mock_dash_repo.obter_evolucao_faturamento.return_value = []
        self.mock_dash_repo.obter_distribuicao_status_pedidos.return_value = []
        self.mock_dash_repo.obter_pedidos_recentes.return_value = []
        self.mock_dash_repo.obter_produtos_mais_vendidos.return_value = []
        self.mock_dash_repo.obter_entregas_em_andamento.return_value = []
        self.mock_dash_repo.obter_atividades_recentes.return_value = []

        self.mock_dash_repo.obter_alertas_gerenciais.return_value = {
            "pedidos_atrasados": 3,
            "entregas_atrasadas": 2,
            "produtos_estoque_critico": 5,
            "contas_receber_vencidas": {"quantidade": 4, "valor": 1200.00},
            "contas_pagar_proximas_vencimento": {"quantidade": 1, "valor": 350.00}
        }

        resultado = self.service.obter_metricas(periodo='hoje')
        alertas = resultado['alertas']

        self.assertEqual(alertas['pedidos_atrasados'], 3)
        self.assertEqual(alertas['produtos_estoque_critico'], 5)
        self.assertEqual(alertas['contas_receber_vencidas']['quantidade'], 4)
        self.assertEqual(alertas['contas_receber_vencidas']['valor'], 1200.00)

    def test_dashboard_repository_evolucao_sql_formatting(self):
        """
        Valida que o método obter_evolucao_faturamento formata a query SQL sem erro
        de interpolação do PyMySQL ('not enough arguments for format string').
        """
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            {'rotulo': '24/11', 'faturamento': 1500.0, 'total_pedidos': 2}
        ]

        repo = DashboardRepository(connection=mock_conn)
        dt_ini = datetime.date(2026, 11, 1)
        dt_fim = datetime.date(2026, 11, 24)

        for agrup in ['dia', 'semana', 'mes']:
            res = repo.obter_evolucao_faturamento(dt_ini, dt_fim, agrupamento=agrup)
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]['rotulo'], '24/11')
            self.assertEqual(res[0]['faturamento'], 1500.0)

            # Garante que cursor.execute foi chamado com a query contendo escapes corretos e 2 parâmetros
            chamada = mock_cursor.execute.call_args
            query_sql = chamada[0][0]
            params = chamada[0][1]
            self.assertEqual(len(params), 2)
            # Teste de mogrify simulado: interpolação com 2 parâmetros não deve estourar TypeError
            escaped = query_sql % ("'2026-11-01 00:00:00'", "'2026-11-24 23:59:59'")
            self.assertIn("2026-11-01", escaped)

if __name__ == '__main__':
    unittest.main()
