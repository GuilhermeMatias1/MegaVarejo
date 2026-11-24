import datetime
from repositories.base_repository import BaseRepository
from database.connection import DatabaseConnection
from models.financeiro import Fornecedor, ContaPagar, TransacaoCaixa, ResumoFinanceiro

class FinanceiroRepository(BaseRepository):
    """
    Repositório de persistência do módulo Financeiro.
    Encapsula consultas diretas de fornecedores, contas a pagar, pagamentos de pedidos
    e o livro-caixa de movimentações financeiras efetivas.
    """

    def __init__(self, connection=None):
        self._connection = connection

    def _get_connection(self):
        return self._connection if self._connection else DatabaseConnection.get_connection()

    def buscar_por_id(self, id: int):
        """Implementação do contrato de BaseRepository buscando conta a pagar por ID."""
        return self.buscar_conta_pagar_por_id(id)

    def listar_todos(self) -> list:
        """Implementação do contrato de BaseRepository listando contas a pagar."""
        return self.listar_contas_pagar()

    # ==========================================
    # 1. FORNECEDORES
    # ==========================================
    def listar_fornecedores(self, busca: str = None) -> list:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                sql = "SELECT id, razao_social, cnpj_cpf, email, telefone, categoria, criado_em FROM fornecedores WHERE 1=1"
                params = []
                if busca and str(busca).strip():
                    sql += " AND (razao_social LIKE %s OR cnpj_cpf LIKE %s OR email LIKE %s)"
                    term = f"%{str(busca).strip()}%"
                    params.extend([term, term, term])
                sql += " ORDER BY razao_social ASC"
                cursor.execute(sql, tuple(params))
                linhas = cursor.fetchall() or []
                return [
                    Fornecedor(
                        id=l['id'],
                        razao_social=l['razao_social'],
                        cnpj_cpf=l.get('cnpj_cpf') or "",
                        email=l.get('email') or "",
                        telefone=l.get('telefone') or "",
                        categoria=l.get('categoria') or "Geral",
                        criado_em=l.get('criado_em')
                    )
                    for l in linhas
                ]
        finally:
            if should_close: conn.close()

    def criar_fornecedor(self, fornecedor: Fornecedor, conn=None) -> int:
        local_conn = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with local_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO fornecedores (razao_social, cnpj_cpf, email, telefone, categoria)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (fornecedor.razao_social, fornecedor.cnpj_cpf, fornecedor.email,
                     fornecedor.telefone, fornecedor.categoria)
                )
                novo_id = cursor.lastrowid
                if conn is None:
                    local_conn.commit()
                return novo_id
        finally:
            if should_close: local_conn.close()

    def buscar_fornecedor_por_id(self, fornecedor_id: int) -> Fornecedor:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM fornecedores WHERE id = %s", (fornecedor_id,))
                l = cursor.fetchone()
                if not l:
                    return None
                return Fornecedor(
                    id=l['id'],
                    razao_social=l['razao_social'],
                    cnpj_cpf=l.get('cnpj_cpf') or "",
                    email=l.get('email') or "",
                    telefone=l.get('telefone') or "",
                    categoria=l.get('categoria') or "Geral",
                    criado_em=l.get('criado_em')
                )
        finally:
            if should_close: conn.close()

    # ==========================================
    # 2. CONTAS A PAGAR
    # ==========================================
    def listar_contas_pagar(self, status: str = None, data_inicio: str = None, data_fim: str = None) -> list:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT cp.*, f.razao_social AS fornecedor_nome
                    FROM contas_pagar cp
                    LEFT JOIN fornecedores f ON f.id = cp.fornecedor_id
                    WHERE 1=1
                """
                params = []
                if data_inicio:
                    sql += " AND cp.data_vencimento >= %s"
                    params.append(data_inicio)
                if data_fim:
                    sql += " AND cp.data_vencimento <= %s"
                    params.append(data_fim)
                if status and status != 'Todos':
                    if status == 'Vencido':
                        sql += " AND cp.status != 'Pago' AND cp.status != 'Cancelado' AND cp.data_vencimento < CURDATE()"
                    else:
                        sql += " AND cp.status = %s"
                        params.append(status)

                sql += " ORDER BY cp.data_vencimento ASC, cp.id DESC"
                cursor.execute(sql, tuple(params))
                linhas = cursor.fetchall() or []
                return [
                    ContaPagar(
                        id=l['id'],
                        descricao=l['descricao'],
                        valor_original=float(l['valor_original']),
                        valor_pago=float(l.get('valor_pago') or 0.0),
                        data_vencimento=l['data_vencimento'],
                        fornecedor_id=l.get('fornecedor_id'),
                        fornecedor_nome=l.get('fornecedor_nome'),
                        categoria=l.get('categoria') or "Operacional",
                        data_pagamento=l.get('data_pagamento'),
                        status=l.get('status') or "Pendente",
                        forma_pagamento=l.get('forma_pagamento'),
                        comprovante=l.get('comprovante'),
                        responsavel=l.get('responsavel') or "Financeiro",
                        observacoes=l.get('observacoes') or "",
                        criado_em=l.get('criado_em')
                    )
                    for l in linhas
                ]
        finally:
            if should_close: conn.close()

    def buscar_conta_pagar_por_id(self, conta_id: int, conn=None, for_update: bool = False) -> ContaPagar:
        local_conn = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with local_conn.cursor() as cursor:
                sql = """
                    SELECT cp.*, f.razao_social AS fornecedor_nome
                    FROM contas_pagar cp
                    LEFT JOIN fornecedores f ON f.id = cp.fornecedor_id
                    WHERE cp.id = %s
                """
                if for_update:
                    sql += " FOR UPDATE"
                cursor.execute(sql, (conta_id,))
                l = cursor.fetchone()
                if not l:
                    return None
                return ContaPagar(
                    id=l['id'],
                    descricao=l['descricao'],
                    valor_original=float(l['valor_original']),
                    valor_pago=float(l.get('valor_pago') or 0.0),
                    data_vencimento=l['data_vencimento'],
                    fornecedor_id=l.get('fornecedor_id'),
                    fornecedor_nome=l.get('fornecedor_nome'),
                    categoria=l.get('categoria') or "Operacional",
                    data_pagamento=l.get('data_pagamento'),
                    status=l.get('status') or "Pendente",
                    forma_pagamento=l.get('forma_pagamento'),
                    comprovante=l.get('comprovante'),
                    responsavel=l.get('responsavel') or "Financeiro",
                    observacoes=l.get('observacoes') or "",
                    criado_em=l.get('criado_em')
                )
        finally:
            if should_close: local_conn.close()

    def criar_conta_pagar(self, conta: ContaPagar, conn=None) -> int:
        local_conn = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with local_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO contas_pagar (descricao, fornecedor_id, categoria, valor_original,
                                             valor_pago, data_vencimento, status, observacoes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (conta.descricao, conta._fornecedor_id, conta.categoria, conta.valor_original,
                     conta.valor_pago, conta.data_vencimento, conta._status, conta._observacoes)
                )
                novo_id = cursor.lastrowid
                if conn is None:
                    local_conn.commit()
                return novo_id
        finally:
            if should_close: local_conn.close()

    def atualizar_pagamento_conta(self, conta: ContaPagar, conn=None):
        local_conn = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with local_conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE contas_pagar
                    SET valor_pago = %s, status = %s, data_pagamento = %s,
                        forma_pagamento = %s, comprovante = %s, responsavel = %s
                    WHERE id = %s
                    """,
                    (conta.valor_pago, conta._status, conta._data_pagamento,
                     conta._forma_pagamento, conta._comprovante, conta._responsavel, conta.id)
                )
                if conn is None:
                    local_conn.commit()
        finally:
            if should_close: local_conn.close()

    # ==========================================
    # 3. CONTAS A RECEBER (PEDIDOS PENDENTES E PARCIAIS)
    # ==========================================
    def listar_contas_receber(self, busca: str = None, data_inicio: str = None, data_fim: str = None) -> list:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        p.id AS pedido_id,
                        p.numero_pedido,
                        p.data_pedido,
                        p.valor_total,
                        p.status AS status_pedido,
                        p.status_pagamento,
                        p.forma_pagamento,
                        c.id AS cliente_id,
                        c.nome AS cliente_nome,
                        c.cpf AS cliente_cpf,
                        COALESCE(SUM(CASE WHEN pr.tipo = 'Pagamento' AND pr.status = 'Confirmado' THEN pr.valor ELSE 0 END), 0.00) AS total_recebido
                    FROM pedidos p
                    LEFT JOIN clientes c ON c.id = p.cliente_id
                    LEFT JOIN pagamentos_reembolsos pr ON pr.pedido_id = p.id
                    WHERE p.status NOT IN ('Cancelado', 'Recusado')
                      AND p.status_pagamento != 'Confirmado'
                """
                params = []
                if data_inicio:
                    sql += " AND p.data_pedido >= %s"
                    params.append(f"{data_inicio} 00:00:00")
                if data_fim:
                    sql += " AND p.data_pedido <= %s"
                    params.append(f"{data_fim} 23:59:59")
                if busca and str(busca).strip():
                    sql += " AND (p.numero_pedido LIKE %s OR c.nome LIKE %s OR c.cpf LIKE %s)"
                    term = f"%{str(busca).strip()}%"
                    params.extend([term, term, term])

                sql += " GROUP BY p.id ORDER BY p.id DESC"
                cursor.execute(sql, tuple(params))
                linhas = cursor.fetchall() or []
                
                resultado = []
                for l in linhas:
                    vt = float(l['valor_total'])
                    rec = float(l['total_recebido'])
                    rest = max(0.0, round(vt - rec, 2))
                    st_calc = "Parcialmente Pago" if rec > 0 and rest > 0 else "Pendente"
                    resultado.append({
                        "pedido_id": l['pedido_id'],
                        "numero_pedido": l['numero_pedido'] or f"PED-{l['pedido_id']}",
                        "data_pedido": formatar_data_br(l['data_pedido']),
                        "cliente_nome": l.get('cliente_nome') or "Cliente Avulso",
                        "cliente_cpf": l.get('cliente_cpf') or "-",
                        "valor_total": vt,
                        "valor_recebido": rec,
                        "valor_restante": rest,
                        "forma_pagamento": l.get('forma_pagamento') or "Boleto Bancário",
                        "status_pedido": l['status_pedido'],
                        "status_pagamento": l['status_pagamento'],
                        "status_calculado": st_calc
                    })
                return resultado
        finally:
            if should_close: conn.close()

    # ==========================================
    # 4. TRANSAÇÕES DE CAIXA E FLUXO DE CAIXA
    # ==========================================
    def registrar_transacao_caixa(self, transacao: TransacaoCaixa, conn=None):
        local_conn = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with local_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO transacoes_caixa 
                    (operacao_id, tipo, origem, referencia_id, valor, forma_pagamento, descricao, responsavel, data_transacao)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (transacao.operacao_id, transacao.tipo, transacao.origem,
                     transacao.referencia_id, transacao.valor, transacao.forma_pagamento,
                     transacao.descricao, transacao.responsavel, transacao.data_transacao)
                )
                if conn is None:
                    local_conn.commit()
        finally:
            if should_close: local_conn.close()

    def existe_operacao_caixa(self, operacao_id: str, conn=None) -> bool:
        local_conn = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with local_conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM transacoes_caixa WHERE operacao_id = %s", (operacao_id,))
                return cursor.fetchone() is not None
        finally:
            if should_close: local_conn.close()

    def registrar_pagamento_reembolso(self, pedido_id: int, tipo: str, valor: float,
                                      forma_pagamento: str, status: str, operacao_id: str,
                                      confirmado_por: str, comprovante: str = None, conn=None):
        local_conn = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with local_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO pagamentos_reembolsos
                    (pedido_id, tipo, valor, forma_pagamento, status, operacao_id, confirmado_por,
                     data_confirmacao, comprovante_ref)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                    """,
                    (pedido_id, tipo, valor, forma_pagamento, status, operacao_id, confirmado_por, comprovante)
                )
                if conn is None:
                    local_conn.commit()
        finally:
            if should_close: local_conn.close()

    def listar_transacoes_caixa(self, tipo: str = None, origem: str = None,
                                data_inicio: str = None, data_fim: str = None) -> list:
        """
        Retorna o extrato cronológico das transações e calcula o saldo acumulado dinamicamente
        a partir do histórico, garantindo consistência matemática absoluta.
        """
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM transacoes_caixa WHERE 1=1"
                params = []
                if data_inicio:
                    sql += " AND data_transacao >= %s"
                    params.append(f"{data_inicio} 00:00:00")
                if data_fim:
                    sql += " AND data_transacao <= %s"
                    params.append(f"{data_fim} 23:59:59")
                if tipo and tipo != 'Todos':
                    sql += " AND tipo = %s"
                    params.append(tipo)
                if origem and origem != 'Todos':
                    sql += " AND origem = %s"
                    params.append(origem)

                sql += " ORDER BY data_transacao ASC, id ASC"
                cursor.execute(sql, tuple(params))
                linhas = cursor.fetchall() or []

                transacoes = []
                saldo_acumulado = 0.0
                for l in linhas:
                    v = float(l['valor'])
                    if l['tipo'] == 'Entrada':
                        saldo_acumulado += v
                    else:
                        saldo_acumulado -= v

                    item = {
                        "id": l['id'],
                        "operacao_id": l['operacao_id'],
                        "tipo": l['tipo'],
                        "origem": l['origem'],
                        "referencia_id": l.get('referencia_id'),
                        "valor": v,
                        "saldo_resultante": round(saldo_acumulado, 2),
                        "forma_pagamento": l.get('forma_pagamento') or "Outros",
                        "descricao": l['descricao'],
                        "responsavel": l['responsavel'],
                        "data_transacao": formatar_data_br(l['data_transacao'])
                    }
                    transacoes.append(item)

                # Para visualização do extrato mais recente primeiro:
                return list(reversed(transacoes))
        finally:
            if should_close: conn.close()

    def obter_resumo_financeiro(self) -> ResumoFinanceiro:
        """
        Calcula os indicadores financeiros globais:
        - Saldo Disponível: a partir da soma histórica de transações de caixa (entradas - saídas).
        - Receitas Totais: pedidos não cancelados/recusados.
        - Despesas Totais: total de despesas e contas a pagar.
        - Contas a Receber: saldo pendente de pedidos.
        - Contas a Pagar Pendentes: saldo não quitado de contas a pagar.
        """
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                # 1. Movimentações efetivas de caixa
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(CASE WHEN tipo = 'Entrada' THEN valor ELSE 0 END), 0.00) AS total_entradas,
                        COALESCE(SUM(CASE WHEN tipo = 'Saída' THEN valor ELSE 0 END), 0.00) AS total_saidas
                    FROM transacoes_caixa
                """)
                cx = cursor.fetchone() or {}
                entradas = float(cx.get('total_entradas') or 0.0)
                saidas = float(cx.get('total_saidas') or 0.0)
                saldo_disp = round(entradas - saidas, 2)

                # 2. Receitas Totais (Competência)
                cursor.execute("""
                    SELECT COALESCE(SUM(valor_total), 0.00) AS total_receitas
                    FROM pedidos
                    WHERE status NOT IN ('Cancelado', 'Recusado')
                """)
                receitas = float(cursor.fetchone().get('total_receitas') or 0.0)

                # 3. Despesas Totais (Competência)
                cursor.execute("""
                    SELECT COALESCE(SUM(valor_original), 0.00) AS total_despesas
                    FROM contas_pagar
                    WHERE status != 'Cancelado'
                """)
                despesas = float(cursor.fetchone().get('total_despesas') or 0.0)

                # 4. Contas a Pagar Pendentes
                cursor.execute("""
                    SELECT COALESCE(SUM(valor_original - valor_pago), 0.00) AS a_pagar_pendente
                    FROM contas_pagar
                    WHERE status IN ('Pendente', 'Parcialmente Pago')
                """)
                a_pagar = float(cursor.fetchone().get('a_pagar_pendente') or 0.0)

                # 5. Contas a Receber Pendentes
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(p.valor_total), 0.00) AS total_pedidos_abertos,
                        COALESCE(SUM(pr.valor_pago), 0.00) AS total_ja_recebido
                    FROM pedidos p
                    LEFT JOIN (
                        SELECT pedido_id, SUM(valor) AS valor_pago
                        FROM pagamentos_reembolsos
                        WHERE tipo = 'Pagamento' AND status = 'Confirmado'
                        GROUP BY pedido_id
                    ) pr ON pr.pedido_id = p.id
                    WHERE p.status NOT IN ('Cancelado', 'Recusado')
                      AND p.status_pagamento != 'Confirmado'
                """)
                rc = cursor.fetchone() or {}
                tot_ped = float(rc.get('total_pedidos_abertos') or 0.0)
                tot_rec = float(rc.get('total_ja_recebido') or 0.0)
                a_receber = max(0.0, round(tot_ped - tot_rec, 2))

                return ResumoFinanceiro(
                    saldo_disponivel=saldo_disp,
                    total_entradas_caixa=entradas,
                    total_saidas_caixa=saidas,
                    receitas_totais=receitas,
                    despesas_totais=despesas,
                    contas_a_receber=a_receber,
                    contas_a_pagar_pendentes=a_pagar
                )
        finally:
            if should_close: conn.close()
