import unittest
import datetime
from unittest.mock import MagicMock, patch
from models.financeiro import ContaReceber, TransacaoCaixa
from models.pedido import Pedido, ItemPedido
from services.pedido_service import PedidoService
from services.financeiro_service import FinanceiroService
from repositories.financeiro_repository import FinanceiroRepository
from repositories.pedido_repository import PedidoRepository
from repositories.produto_repository import ProdutoRepository
from repositories.movimentacao_repository import MovimentacaoRepository

class TestIntegracaoFinanceira(unittest.TestCase):
    def setUp(self):
        self.mock_fin_repo = MagicMock(spec=FinanceiroRepository)
        self.mock_ped_repo = MagicMock(spec=PedidoRepository)
        self.mock_prod_repo = MagicMock(spec=ProdutoRepository)
        self.mock_mov_repo = MagicMock(spec=MovimentacaoRepository)

        self.pedido_service = PedidoService(
            pedido_repo=self.mock_ped_repo,
            produto_repo=self.mock_prod_repo,
            mov_repo=self.mock_mov_repo,
            financeiro_repo=self.mock_fin_repo
        )
        self.financeiro_service = FinanceiroService(
            financeiro_repo=self.mock_fin_repo,
            pedido_repo=self.mock_ped_repo
        )

    def test_modelo_conta_receber_status_calculado(self):
        """Valida máquina de status calculados da ContaReceber: Pendente, Parcialmente Pago, Pago, Vencido, Cancelado"""
        hoje = datetime.date.today()
        amanha = hoje + datetime.timedelta(days=1)
        ontem = hoje - datetime.timedelta(days=1)

        # 1. Pendente no prazo
        cr = ContaReceber(pedido_id=1, cliente_id=10, valor_original=100.0, valor_recebido=0.0, data_vencimento=amanha)
        self.assertEqual(cr.status_calculado, 'Pendente')
        self.assertEqual(cr.valor_restante, 100.0)

        # 2. Vencido
        cr_vencida = ContaReceber(pedido_id=2, cliente_id=10, valor_original=100.0, valor_recebido=0.0, data_vencimento=ontem)
        self.assertEqual(cr_vencida.status_calculado, 'Vencido')

        # 3. Parcialmente Pago
        cr.registrar_recebimento(40.0)
        self.assertEqual(cr.valor_recebido, 40.0)
        self.assertEqual(cr.valor_restante, 60.0)
        self.assertEqual(cr.status_calculado, 'Parcialmente Pago')

        # 4. Totalmente Pago
        cr.registrar_recebimento(60.0)
        self.assertEqual(cr.valor_recebido, 100.0)
        self.assertEqual(cr.valor_restante, 0.0)
        self.assertEqual(cr.status_calculado, 'Pago')

        # 5. Cancelado
        cr2 = ContaReceber(pedido_id=3, cliente_id=10, valor_original=50.0, valor_recebido=0.0, data_vencimento=amanha)
        cr2.cancelar()
        self.assertEqual(cr2.status_calculado, 'Cancelado')

    def test_recebimento_excedente_rejeitado(self):
        """Não permite registrar recebimento maior que o saldo restante"""
        cr = ContaReceber(pedido_id=1, cliente_id=10, valor_original=100.0, valor_recebido=50.0, data_vencimento=datetime.date.today())
        with self.assertRaises(ValueError):
            cr.registrar_recebimento(60.0)

    def test_permissao_rbac_confirmar_pagamento(self):
        """Vendas ou Estoque não podem confirmar pagamento de pedidos"""
        with self.assertRaises(PermissionError):
            self.pedido_service.confirmar_pagamento(
                pedido_id=1,
                responsavel="Vendedor",
                usuario_perfil="Vendas"
            )

        with self.assertRaises(PermissionError):
            self.pedido_service.confirmar_pagamento(
                pedido_id=1,
                responsavel="Estoquista",
                usuario_perfil="Estoque"
            )

    @patch('database.connection.DatabaseConnection.get_connection')
    def test_confirmar_pagamento_parcial_e_total(self, mock_get_conn):
        """Valida pagamento parcial seguido de total com baixa na ContaReceber e entrada no Caixa"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        cursor_mock = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = cursor_mock
        cursor_mock.fetchone.return_value = {'total_recebido': 0.0}

        pedido = Pedido(
            id=101,
            cliente_id=5,
            valor_total=200.0,
            status="Aguardando Pagamento",
            status_pagamento="Pendente"
        )
        pedido.adicionar_item(ItemPedido(produto_id=1, quantidade=1, preco_unitario=200.0, produto_nome="Teste"))
        self.mock_ped_repo.buscar_por_id.return_value = pedido
        self.mock_fin_repo.existe_operacao_caixa.return_value = False

        conta_receber = ContaReceber(
            pedido_id=101,
            cliente_id=5,
            valor_original=200.0,
            valor_recebido=0.0,
            data_vencimento=datetime.date.today() + datetime.timedelta(days=5)
        )
        self.mock_fin_repo.buscar_conta_receber_por_pedido.return_value = conta_receber

        # 1. Pagamento Parcial de 80.00
        res_parcial = self.pedido_service.confirmar_pagamento(
            pedido_id=101,
            responsavel="Analista Financeiro",
            usuario_perfil="Financeiro",
            valor=80.0
        )
        self.assertEqual(res_parcial['status_pagamento'], 'Parcialmente Pago')
        self.assertEqual(res_parcial['saldo_restante'], 120.0)
        self.assertEqual(conta_receber.valor_recebido, 80.0)
        self.assertEqual(conta_receber.status_calculado, 'Parcialmente Pago')

        # Verifica chamada ao caixa
        self.mock_fin_repo.registrar_transacao_caixa.assert_called()
        chamada_caixa = self.mock_fin_repo.registrar_transacao_caixa.call_args[0][0]
        self.assertEqual(chamada_caixa.tipo, 'Entrada')
        self.assertEqual(chamada_caixa.valor, 80.0)
        self.assertEqual(chamada_caixa.origem, 'Pedido')

        # 2. Pagamento do saldo restante (120.00)
        cursor_mock.fetchone.return_value = {'total_recebido': 80.0}
        res_total = self.pedido_service.confirmar_pagamento(
            pedido_id=101,
            responsavel="Analista Financeiro",
            usuario_perfil="Financeiro",
            valor=120.0
        )
        self.assertEqual(res_total['status_pagamento'], 'Confirmado')
        self.assertEqual(res_total['saldo_restante'], 0.0)
        self.assertEqual(conta_receber.valor_recebido, 200.0)
        self.assertEqual(conta_receber.status_calculado, 'Pago')

    @patch('database.connection.DatabaseConnection.get_connection')
    def test_cancelamento_pedido_cancela_conta_receber(self, mock_get_conn):
        """Ao cancelar um pedido, a conta a receber vinculada deve ser cancelada"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        pedido = Pedido(
            id=102,
            cliente_id=5,
            valor_total=150.0,
            status="Aguardando Pagamento",
            status_pagamento="Pendente"
        )
        self.mock_ped_repo.buscar_por_id.return_value = pedido

        conta_receber = ContaReceber(
            pedido_id=102,
            cliente_id=5,
            valor_original=150.0,
            valor_recebido=0.0,
            data_vencimento=datetime.date.today() + datetime.timedelta(days=2)
        )
        self.mock_fin_repo.buscar_conta_receber_por_pedido.return_value = conta_receber

        self.pedido_service.cancelar_pedido(
            pedido_id=102,
            motivo="Cliente desistiu da compra",
            responsavel="Vendedor"
        )

        self.assertEqual(conta_receber.status_calculado, 'Cancelado')
        self.mock_fin_repo.atualizar_conta_receber.assert_called_with(conta_receber, conn=mock_conn)

    @patch('database.connection.DatabaseConnection.get_connection')
    def test_estorno_reembolso_gera_saida_caixa_e_atualiza_conta_receber(self, mock_get_conn):
        """Estorno/Reembolso registra Saída no caixa e atualiza a ContaReceber proporcionalmente"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn

        pedido = Pedido(
            id=103,
            cliente_id=8,
            valor_total=300.0,
            status="Cancelado",
            status_pagamento="Confirmado"
        )
        self.mock_ped_repo.buscar_por_id.return_value = pedido
        self.mock_fin_repo.existe_operacao_caixa.return_value = False

        conta_receber = ContaReceber(
            pedido_id=103,
            cliente_id=8,
            valor_original=300.0,
            valor_recebido=300.0,
            data_vencimento=datetime.date.today()
        )
        self.mock_fin_repo.buscar_conta_receber_por_pedido.return_value = conta_receber

        resultado = self.financeiro_service.estornar_pagamento_pedido(
            pedido_id=103,
            valor=300.0,
            motivo="Devolução total aprovada",
            responsavel="Gerente Financeiro"
        )

        self.assertIn("sucesso", resultado['mensagem'])
        self.mock_fin_repo.registrar_transacao_caixa.assert_called()
        transacao_saida = self.mock_fin_repo.registrar_transacao_caixa.call_args[0][0]
        self.assertEqual(transacao_saida.tipo, 'Saída')
        self.assertEqual(transacao_saida.origem, 'Estorno')
        self.assertEqual(transacao_saida.valor, 300.0)

        self.assertEqual(conta_receber.valor_recebido, 0.0)
        self.assertEqual(conta_receber.status_calculado, 'Cancelado')
        self.mock_fin_repo.atualizar_conta_receber.assert_called_with(conta_receber, conn=mock_conn)

    @patch('database.connection.DatabaseConnection.get_connection')
    def test_prevencao_duplicidade_idempotencia_caixa(self, mock_get_conn):
        """Garante que operações com o mesmo operacao_id sejam rejeitadas"""
        mock_conn = MagicMock()
        mock_get_conn.return_value = mock_conn
        self.mock_fin_repo.existe_operacao_caixa.return_value = True

        pedido = Pedido(id=104, cliente_id=2, valor_total=100.0, status="Aguardando Pagamento", status_pagamento="Pendente")
        self.mock_ped_repo.buscar_por_id.return_value = pedido

        with self.assertRaises(ValueError) as ctx:
            self.pedido_service.confirmar_pagamento(
                pedido_id=104,
                responsavel="Financeiro",
                usuario_perfil="Financeiro",
                transacao_id="OP-DUPLICADA-123"
            )
        self.assertIn("já foi registrada", str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
