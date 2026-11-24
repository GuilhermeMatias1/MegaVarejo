"""
Suíte de testes automatizados para o Módulo Financeiro do MegaVarejo ERP.
Testa regras de negócio, POO, fluxo de caixa efetivo, prevenção de duplicidades,
cálculo de status (Vencido, Parcialmente Pago), estornos e permissões RBAC.
"""

import unittest
import datetime
from unittest.mock import patch, MagicMock
from models.financeiro import Fornecedor, ContaPagar, TransacaoCaixa, ResumoFinanceiro
from services.financeiro_service import FinanceiroService
from app import app, ROLE_PERMISSIONS

class TestModuloFinanceiro(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-financeiro'
        self.client = app.test_client()

    # ==========================================
    # 1. TESTES DE DOMÍNIO E POO
    # ==========================================
    def test_encapsulamento_fornecedor(self):
        f = Fornecedor(razao_social="Tech Distribuidora", cnpj_cpf="12.345.678/0001-90", email="contato@tech.com")
        self.assertEqual(f.razao_social, "Tech Distribuidora")
        self.assertEqual(f.cnpj_cpf, "12.345.678/0001-90")
        
        with self.assertRaises(ValueError):
            f.razao_social = ""
        with self.assertRaises(ValueError):
            f.email = "invalido"

    def test_conta_pagar_status_calculado_e_parcial(self):
        hoje = datetime.date.today()
        ontem = hoje - datetime.timedelta(days=1)
        amanha = hoje + datetime.timedelta(days=1)

        # 1. Conta no prazo e sem pagamento -> Pendente
        cp1 = ContaPagar(descricao="Aluguel", valor_original=1000.0, data_vencimento=amanha)
        self.assertEqual(cp1.status_calculado, "Pendente")
        self.assertEqual(cp1.valor_restante, 1000.0)

        # 2. Pagamento parcial dentro do prazo -> Parcialmente Pago
        cp1.registrar_pagamento(valor=400.0, forma_pagamento="PIX", responsavel="Financeiro")
        self.assertEqual(cp1.status_calculado, "Parcialmente Pago")
        self.assertEqual(cp1.valor_restante, 600.0)

        # 3. Quitação total -> Pago
        cp1.registrar_pagamento(valor=600.0, forma_pagamento="PIX", responsavel="Financeiro")
        self.assertEqual(cp1.status_calculado, "Pago")
        self.assertEqual(cp1.valor_restante, 0.0)

        # 4. Conta não paga após vencimento -> Vencido (calculado dinamicamente)
        cp2 = ContaPagar(descricao="Energia", valor_original=300.0, data_vencimento=ontem)
        self.assertEqual(cp2.status_calculado, "Vencido")

        # 5. Tentativa de pagar valor superior ao saldo restante -> Rejeitada
        with self.assertRaises(ValueError):
            cp2.registrar_pagamento(valor=500.0, forma_pagamento="PIX", responsavel="Financeiro")

    def test_transacao_caixa_idempotencia_e_validacoes(self):
        with self.assertRaises(ValueError):
            # operacao_id obrigatório
            TransacaoCaixa(operacao_id="", tipo="Entrada", origem="Pedido", valor=100.0, descricao="Teste", responsavel="Admin")

        with self.assertRaises(ValueError):
            # Valor deve ser positivo maior que zero
            TransacaoCaixa(operacao_id="OP-123", tipo="Entrada", origem="Pedido", valor=-50.0, descricao="Teste", responsavel="Admin")

        t = TransacaoCaixa(operacao_id="OP-001", tipo="Entrada", origem="Pedido", valor=250.0, descricao="Recebimento", responsavel="Financeiro")
        self.assertEqual(t.operacao_id, "OP-001")
        self.assertEqual(t.valor, 250.0)

    def test_resumo_financeiro_diferenciacao_caixa_e_resultado(self):
        """
        Garante que o Saldo de Caixa não seja confundido com o Resultado Operacional Simplificado.
        """
        # Exemplo:
        # Vendas totais faturadas (Receitas): R$ 10.000,00
        # Despesas incorridas: R$ 4.000,00
        # Porém, apenas R$ 2.000,00 foram recebidos no caixa e R$ 1.000,00 foram pagos
        resumo = ResumoFinanceiro(
            saldo_disponivel=1000.0,         # R$ 2000 recebidos - R$ 1000 pagos
            total_entradas_caixa=2000.0,
            total_saidas_caixa=1000.0,
            receitas_totais=10000.0,
            despesas_totais=4000.0,
            contas_a_receber=8000.0,
            contas_a_pagar_pendentes=3000.0
        )
        self.assertEqual(resumo.saldo_disponivel, 1000.0)
        self.assertEqual(resumo.resultado_operacional_simplificado, 6000.0) # 10000 - 4000
        self.assertNotEqual(resumo.saldo_disponivel, resumo.resultado_operacional_simplificado)

    # ==========================================
    # 2. TESTES DE SERVIÇO E REGRAS DE NEGÓCIO
    # ==========================================
    @patch('services.financeiro_service.DatabaseConnection.get_connection')
    def test_pagamento_duplicado_bloqueado_por_operacao_id(self, mock_db_conn):
        mock_conn = MagicMock()
        mock_db_conn.return_value = mock_conn

        mock_repo = MagicMock()
        mock_repo.existe_operacao_caixa.return_value = True # Simula que a operação já existe

        service = FinanceiroService(financeiro_repo=mock_repo)

        # Tentativa com operacao_id já registrado deve falhar imediatamente
        with self.assertRaises(ValueError) as ctx:
            service.pagar_conta(conta_id=1, valor=150.0, forma_pagamento="PIX", responsavel="Admin", operacao_id="OP-DUP-01")
        self.assertIn("já foi processada", str(ctx.exception))

    @patch('services.financeiro_service.DatabaseConnection.get_connection')
    def test_estorno_preserva_historico_sem_apagar_dados(self, mock_db_conn):
        mock_conn = MagicMock()
        mock_db_conn.return_value = mock_conn

        mock_fin_repo = MagicMock()
        mock_ped_repo = MagicMock()

        mock_fin_repo.existe_operacao_caixa.return_value = False
        mock_pedido = MagicMock()
        mock_pedido.id = 10
        mock_pedido.numero_pedido = "PED-10"
        mock_pedido.forma_pagamento = "PIX"
        mock_ped_repo.buscar_por_id.return_value = mock_pedido

        service = FinanceiroService(financeiro_repo=mock_fin_repo, pedido_repo=mock_ped_repo)
        res = service.estornar_pagamento_pedido(
            pedido_id=10,
            valor=250.0,
            motivo="Devolução de cliente",
            responsavel="Gerente",
            operacao_id="EST-TEST-01"
        )

        self.assertIn("sucesso", res["mensagem"])
        # Garante que registrou contrapartida em pagamentos_reembolsos e saída no caixa
        mock_fin_repo.registrar_pagamento_reembolso.assert_called_once()
        mock_fin_repo.registrar_transacao_caixa.assert_called_once()
        # Garante que commitou a transação
        mock_conn.commit.assert_called_once()

    # ==========================================
    # 3. TESTES DE ROTAS E RBAC
    # ==========================================
    def test_rotas_financeiro_bloqueadas_sem_login(self):
        rotas = [
            '/api/financeiro/visao-geral',
            '/api/financeiro/contas-pagar',
            '/api/financeiro/contas-receber',
            '/api/financeiro/fluxo-caixa',
            '/api/financeiro/fornecedores'
        ]
        for r in rotas:
            res = self.client.get(r)
            self.assertEqual(res.status_code, 401, f"Rota {r} deveria requerer login.")

    def test_rotas_financeiro_bloqueadas_para_vendedor_e_estoquista(self):
        perfis_negados = ['Vendas', 'Estoque']
        rotas = ['/api/financeiro/visao-geral', '/api/financeiro/contas-pagar']

        for perfil in perfis_negados:
            with self.client.session_transaction() as sess:
                sess['usuario_id'] = 99
                sess['usuario_nome'] = 'Operador Sem Acesso'
                sess['usuario_perfil'] = perfil

            for r in rotas:
                res = self.client.get(r)
                self.assertEqual(res.status_code, 403, f"Perfil {perfil} não deveria acessar {r}.")

    @patch('app.financeiro_service.obter_visao_geral')
    def test_rotas_financeiro_permitidas_para_financeiro_gerencia_admin(self, mock_visao):
        mock_visao.return_value = {
            "saldo_disponivel": 1500.0,
            "receitas_totais": 5000.0,
            "despesas_totais": 3500.0,
            "resultado_operacional_simplificado": 1500.0,
            "contas_a_receber": 2000.0,
            "contas_a_pagar_pendentes": 500.0
        }
        perfis_permitidos = ['Financeiro', 'Gerência', 'Administrador']

        for perfil in perfis_permitidos:
            with self.client.session_transaction() as sess:
                sess['usuario_id'] = 1
                sess['usuario_nome'] = f'Operador {perfil}'
                sess['usuario_perfil'] = perfil

            res = self.client.get('/api/financeiro/visao-geral')
            self.assertEqual(res.status_code, 200, f"Perfil {perfil} deveria ter acesso à rota.")
            dados = res.get_json()
            self.assertEqual(dados['saldo_disponivel'], 1500.0)


if __name__ == '__main__':
    unittest.main()
