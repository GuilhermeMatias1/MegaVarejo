import uuid
from decimal import Decimal
from database.connection import DatabaseConnection
from repositories.financeiro_repository import FinanceiroRepository
from repositories.pedido_repository import PedidoRepository
from models.financeiro import Fornecedor, ContaPagar, TransacaoCaixa, ResumoFinanceiro

class FinanceiroService:
    """
    Camada de Serviço do Módulo Financeiro.
    Orquestra as operações financeiras em transações SQL atômicas:
    - Prevenção contra pagamentos duplicados via operacao_id e checagem de saldo residual.
    - Suporte a pagamentos parciais legítimos.
    - Atualização do livro-caixa apenas com movimentações financeiras efetivas.
    - Tratamento de estornos e reembolsos com preservação do histórico.
    """

    def __init__(self, financeiro_repo: FinanceiroRepository = None, pedido_repo: PedidoRepository = None):
        self._financeiro_repo = financeiro_repo or FinanceiroRepository()
        self._pedido_repo = pedido_repo or PedidoRepository()

    # ==========================================
    # 1. RESUMO FINANCEIRO E INDICADORES
    # ==========================================
    def obter_visao_geral(self) -> dict:
        resumo = self._financeiro_repo.obter_resumo_financeiro()
        return resumo.to_dict()

    # ==========================================
    # 2. FORNECEDORES
    # ==========================================
    def listar_fornecedores(self, busca: str = None) -> list:
        fornecedores = self._financeiro_repo.listar_fornecedores(busca)
        return [f.to_dict() for f in fornecedores]

    def cadastrar_fornecedor(self, razao_social: str, cnpj_cpf: str = "", email: str = "",
                             telefone: str = "", categoria: str = "Geral") -> dict:
        fornecedor = Fornecedor(
            razao_social=razao_social,
            cnpj_cpf=cnpj_cpf,
            email=email,
            telefone=telefone,
            categoria=categoria
        )
        novo_id = self._financeiro_repo.criar_fornecedor(fornecedor)
        return {"id": novo_id, "mensagem": f"Fornecedor '{fornecedor.razao_social}' cadastrado com sucesso!"}

    # ==========================================
    # 3. CONTAS A PAGAR
    # ==========================================
    def listar_contas_pagar(self, status: str = None, data_inicio: str = None, data_fim: str = None) -> list:
        contas = self._financeiro_repo.listar_contas_pagar(status, data_inicio, data_fim)
        return [c.to_dict() for c in contas]

    def cadastrar_conta_pagar(self, descricao: str, valor: float, data_vencimento: str,
                              fornecedor_id: int = None, categoria: str = "Operacional",
                              observacoes: str = "") -> dict:
        conta = ContaPagar(
            descricao=descricao,
            valor_original=valor,
            data_vencimento=data_vencimento,
            fornecedor_id=fornecedor_id,
            categoria=categoria,
            observacoes=observacoes
        )
        novo_id = self._financeiro_repo.criar_conta_pagar(conta)
        return {"id": novo_id, "mensagem": "Conta a pagar cadastrada com sucesso!"}

    def pagar_conta(self, conta_id: int, valor: float, forma_pagamento: str,
                    responsavel: str, operacao_id: str = None, comprovante: str = None) -> dict:
        """
        Executa a baixa (parcial ou total) de uma conta a pagar de forma transacional e atômica:
        - Bloqueia e valida duplicidade de operacao_id.
        - Registra a saída no livro-caixa efetivo.
        - Atualiza a conta a pagar para 'Pago' ou 'Parcialmente Pago'.
        """
        if not operacao_id:
            operacao_id = f"CP-{conta_id}-{uuid.uuid4().hex[:12]}"

        conn = DatabaseConnection.get_connection()
        try:
            # 1. Verifica idempotência
            if self._financeiro_repo.existe_operacao_caixa(operacao_id, conn=conn):
                raise ValueError("Esta operação de pagamento já foi processada anteriormente.")

            # 2. Busca conta com lock
            conta = self._financeiro_repo.buscar_conta_pagar_por_id(conta_id, conn=conn, for_update=True)
            if not conta:
                raise KeyError("Conta a pagar não encontrada.")

            if conta._status == 'Cancelado':
                raise ValueError("Não é possível pagar uma conta cancelada.")
            if conta.valor_restante <= 0:
                raise ValueError("Esta conta já está totalmente quitada.")

            # 3. Registra pagamento na entidade de domínio (valida limites e saldo restante)
            conta.registrar_pagamento(
                valor=valor,
                forma_pagamento=forma_pagamento,
                responsavel=responsavel,
                comprovante=comprovante
            )

            # 4. Atualiza no banco
            self._financeiro_repo.atualizar_pagamento_conta(conta, conn=conn)

            # 5. Registra saída no livro-caixa efetivo
            transacao = TransacaoCaixa(
                operacao_id=operacao_id,
                tipo='Saída',
                origem='Conta a Pagar',
                referencia_id=conta.id,
                valor=valor,
                forma_pagamento=forma_pagamento,
                descricao=f"Pagamento {conta.status_calculado}: {conta.descricao}",
                responsavel=responsavel
            )
            self._financeiro_repo.registrar_transacao_caixa(transacao, conn=conn)

            conn.commit()
            return {
                "mensagem": f"Pagamento de R$ {valor:.2f} registrado com sucesso!",
                "status_conta": conta.status_calculado,
                "valor_restante": conta.valor_restante
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ==========================================
    # 4. CONTAS A RECEBER E RECEBIMENTO DE PEDIDOS
    # ==========================================
    def listar_contas_receber(self, busca: str = None, data_inicio: str = None, data_fim: str = None) -> list:
        return self._financeiro_repo.listar_contas_receber(busca, data_inicio, data_fim)

    def receber_pagamento_pedido(self, pedido_id: int, valor: float, forma_pagamento: str,
                                 responsavel: str, operacao_id: str = None,
                                 comprovante: str = None) -> dict:
        """
        Confirma recebimento (parcial ou total) de um pedido:
        - Garante idempotência via operacao_id.
        - Registra em pagamentos_reembolsos.
        - Se o pedido atingir a quitação total, atualiza status_pagamento para 'Confirmado'
          e o status do pedido para 'Confirmado' / 'Aguardando Separação'.
        - Registra entrada imediata no livro-caixa efetivo.
        """
        if not operacao_id:
            operacao_id = f"PED-{pedido_id}-{uuid.uuid4().hex[:12]}"

        conn = DatabaseConnection.get_connection()
        try:
            # 1. Verifica idempotência
            if self._financeiro_repo.existe_operacao_caixa(operacao_id, conn=conn):
                raise ValueError("Esta transação de recebimento já foi processada.")

            # 2. Busca pedido com lock
            pedido = self._pedido_repo.buscar_por_id(pedido_id)
            if not pedido:
                raise KeyError("Pedido não encontrado.")

            if pedido.status in ['Cancelado', 'Devolvido', 'Recusado']:
                raise ValueError(f"Não é possível receber pagamentos de um pedido com status '{pedido.status}'.")

            # 3. Calcula total já recebido anteriormente
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(valor), 0.00) AS total_recebido
                    FROM pagamentos_reembolsos
                    WHERE pedido_id = %s AND tipo = 'Pagamento' AND status = 'Confirmado'
                    FOR UPDATE
                    """,
                    (pedido_id,)
                )
                total_ja_recebido = float(cursor.fetchone().get('total_recebido') or 0.0)

            saldo_restante = max(0.0, round(pedido.valor_total - total_ja_recebido, 2))
            v = round(float(valor or 0.0), 2)
            if v <= 0:
                raise ValueError("O valor recebido deve ser positivo maior que zero.")
            if v > saldo_restante + 0.001:
                raise ValueError(f"O valor informado (R$ {v:.2f}) excede o saldo restante do pedido (R$ {saldo_restante:.2f}).")

            # 4. Registra histórico em pagamentos_reembolsos
            self._financeiro_repo.registrar_pagamento_reembolso(
                pedido_id=pedido.id,
                tipo='Pagamento',
                valor=v,
                forma_pagamento=forma_pagamento,
                status='Confirmado',
                operacao_id=operacao_id,
                confirmado_por=responsavel,
                comprovante=comprovante,
                conn=conn
            )

            novo_total_recebido = round(total_ja_recebido + v, 2)
            esta_quitado = novo_total_recebido >= round(pedido.valor_total, 2) - 0.001

            # 5. Atualiza status no pedido
            if esta_quitado:
                self._pedido_repo.atualizar_status_pagamento(pedido.id, "Confirmado", conn=conn)
                if pedido.status == 'Aguardando Pagamento':
                    self._pedido_repo.atualizar_status(pedido.id, "Confirmado", conn=conn)
                st_pag_msg = "Confirmado"
            else:
                self._pedido_repo.atualizar_status_pagamento(pedido.id, "Parcialmente Pago", conn=conn)
                st_pag_msg = "Parcialmente Pago"

            # 6. Registra auditoria no histórico de pedidos
            self._pedido_repo.registrar_historico(
                pedido_id=pedido.id,
                status_anterior=pedido.status_pagamento,
                status_novo=st_pag_msg,
                responsavel=responsavel,
                tipo_alteracao="Pagamento",
                observacao=f"Recebimento de R$ {v:.2f} ({forma_pagamento}). Operação: {operacao_id}",
                conn=conn
            )

            # 7. Registra entrada efetiva no caixa
            transacao = TransacaoCaixa(
                operacao_id=operacao_id,
                tipo='Entrada',
                origem='Pedido',
                referencia_id=pedido.id,
                valor=v,
                forma_pagamento=forma_pagamento,
                descricao=f"Recebimento de Pedido #{pedido.numero_pedido or pedido.id} ({st_pag_msg})",
                responsavel=responsavel
            )
            self._financeiro_repo.registrar_transacao_caixa(transacao, conn=conn)

            conn.commit()
            return {
                "mensagem": f"Recebimento de R$ {v:.2f} confirmado com sucesso!",
                "status_pagamento": st_pag_msg,
                "saldo_restante": max(0.0, round(pedido.valor_total - novo_total_recebido, 2))
            }
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def estornar_pagamento_pedido(self, pedido_id: int, valor: float, motivo: str,
                                  responsavel: str, operacao_id: str = None) -> dict:
        """
        Executa o estorno/reembolso de valor de um pedido sem apagar registros:
        - Insere lançamento de contrapartida em pagamentos_reembolsos ('Reembolso' / 'Confirmado').
        - Insere saída efetiva de caixa com origem 'Estorno'.
        - Registra auditoria.
        """
        if not operacao_id:
            operacao_id = f"EST-{pedido_id}-{uuid.uuid4().hex[:12]}"

        conn = DatabaseConnection.get_connection()
        try:
            if self._financeiro_repo.existe_operacao_caixa(operacao_id, conn=conn):
                raise ValueError("Este estorno já foi processado anteriormente.")

            pedido = self._pedido_repo.buscar_por_id(pedido_id)
            if not pedido:
                raise KeyError("Pedido não encontrado.")

            v = round(float(valor or 0.0), 2)
            if v <= 0:
                raise ValueError("O valor de estorno deve ser maior que zero.")

            # Registra contrapartida em pagamentos_reembolsos
            self._financeiro_repo.registrar_pagamento_reembolso(
                pedido_id=pedido.id,
                tipo='Reembolso',
                valor=v,
                forma_pagamento=pedido.forma_pagamento or "Estorno",
                status='Confirmado',
                operacao_id=operacao_id,
                confirmado_por=responsavel,
                comprovante=motivo,
                conn=conn
            )

            # Atualiza status do pedido se integral
            self._pedido_repo.atualizar_status_pagamento(pedido.id, "Reembolsado", conn=conn)
            self._pedido_repo.registrar_historico(
                pedido_id=pedido.id,
                status_anterior=pedido.status_pagamento,
                status_novo="Reembolsado",
                responsavel=responsavel,
                tipo_alteracao="Estorno",
                observacao=f"Estorno/Reembolso de R$ {v:.2f}. Motivo: {motivo}",
                conn=conn
            )

            # Registra saída de caixa
            transacao = TransacaoCaixa(
                operacao_id=operacao_id,
                tipo='Saída',
                origem='Estorno',
                referencia_id=pedido.id,
                valor=v,
                forma_pagamento=pedido.forma_pagamento or "Outros",
                descricao=f"Estorno ref. Pedido #{pedido.numero_pedido or pedido.id}: {motivo}",
                responsavel=responsavel
            )
            self._financeiro_repo.registrar_transacao_caixa(transacao, conn=conn)

            conn.commit()
            return {"mensagem": f"Estorno de R$ {v:.2f} realizado com sucesso!"}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ==========================================
    # 5. FLUXO DE CAIXA E EXTRATO DE TRANSAÇÕES
    # ==========================================
    def listar_fluxo_caixa(self, tipo: str = None, origem: str = None,
                           data_inicio: str = None, data_fim: str = None) -> list:
        return self._financeiro_repo.listar_transacoes_caixa(tipo, origem, data_inicio, data_fim)
