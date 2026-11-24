from repositories.base_repository import BaseRepository
from models.pedido import Pedido, ItemPedido, formatar_data_br
from database.connection import DatabaseConnection

class PedidoRepository(BaseRepository):
    """
    Repositório de persistência para as entidades Pedido, Itens, Histórico e Cancelamentos/Devoluções.
    Encapsula consultas SQL diretas, joins com clientes e operações transacionais.
    """

    def __init__(self, connection=None):
        self._connection = connection

    def _get_connection(self):
        return self._connection if self._connection else DatabaseConnection.get_connection()

    def _mapear_linha(self, l) -> Pedido:
        return Pedido(
            id=l['id'],
            numero_pedido=l.get('numero_pedido'),
            cliente_id=l.get('cliente_id'),
            cliente_nome=l.get('cliente_nome') or "Cliente não informado",
            cliente_cpf=l.get('cliente_cpf') or "-",
            data_pedido=l['data_pedido'],
            data_prevista_entrega=l.get('data_prevista_entrega'),
            status=l['status'],
            status_pagamento=l.get('status_pagamento') or 'Pendente',
            forma_pagamento=l.get('forma_pagamento') or 'Boleto Bancário',
            desconto=l.get('desconto') or 0.0,
            frete=l.get('frete') or 0.0,
            valor_total=l['valor_total'],
            endereco_entrega=l.get('endereco_entrega') or "",
            responsavel=l.get('responsavel') or "Vendedor",
            observacoes=l.get('observacoes') or ""
        )

    def listar_todos(self, busca: str = None, status_pedido: str = None, status_pagamento: str = None,
                     data_inicio: str = None, data_fim: str = None, apenas_atrasados: bool = False) -> list:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                query = """
                    SELECT 
                        p.id, 
                        COALESCE(p.numero_pedido, CONCAT('PED-', LPAD(p.id, 4, '0'))) as numero_pedido,
                        p.cliente_id,
                        c.nome as cliente_nome,
                        c.cpf as cliente_cpf,
                        p.data_pedido, 
                        p.data_prevista_entrega,
                        p.status, 
                        COALESCE(p.status_pagamento, 'Pendente') as status_pagamento,
                        COALESCE(p.forma_pagamento, 'Boleto Bancário') as forma_pagamento,
                        COALESCE(p.valor_subtotal, p.valor_total) as valor_subtotal,
                        COALESCE(p.desconto, 0.0) as desconto,
                        COALESCE(p.frete, 0.0) as frete,
                        CAST(p.valor_total AS FLOAT) as valor_total,
                        p.endereco_entrega,
                        COALESCE(p.responsavel, 'Vendedor') as responsavel,
                        p.observacoes
                    FROM pedidos p
                    LEFT JOIN clientes c ON p.cliente_id = c.id
                    WHERE 1=1
                """
                params = []

                if busca and str(busca).strip():
                    termo = f"%{str(busca).strip()}%"
                    query += " AND (p.numero_pedido LIKE %s OR CAST(p.id AS CHAR) LIKE %s OR c.nome LIKE %s OR c.cpf LIKE %s)"
                    params.extend([termo, termo, termo, termo])

                if status_pedido and str(status_pedido).strip():
                    query += " AND p.status = %s"
                    params.append(str(status_pedido).strip())

                if status_pagamento and str(status_pagamento).strip():
                    query += " AND p.status_pagamento = %s"
                    params.append(str(status_pagamento).strip())

                if data_inicio:
                    query += " AND DATE(p.data_pedido) >= %s"
                    params.append(str(data_inicio))

                if data_fim:
                    query += " AND DATE(p.data_pedido) <= %s"
                    params.append(str(data_fim))

                if apenas_atrasados:
                    query += " AND p.data_prevista_entrega IS NOT NULL AND p.data_prevista_entrega < CURDATE() AND p.status NOT IN ('Entregue', 'Cancelado', 'Devolvido', 'Recusado')"

                query += " ORDER BY p.id DESC;"

                cursor.execute(query, tuple(params))
                linhas = cursor.fetchall()
                return [self._mapear_linha(l) for l in linhas]
        finally:
            if should_close:
                conn.close()

    def buscar_por_id(self, id: int) -> Pedido:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.id, 
                        COALESCE(p.numero_pedido, CONCAT('PED-', LPAD(p.id, 4, '0'))) as numero_pedido,
                        p.cliente_id,
                        c.nome as cliente_nome,
                        c.cpf as cliente_cpf,
                        p.data_pedido, 
                        p.data_prevista_entrega,
                        p.status, 
                        COALESCE(p.status_pagamento, 'Pendente') as status_pagamento,
                        COALESCE(p.forma_pagamento, 'Boleto Bancário') as forma_pagamento,
                        COALESCE(p.valor_subtotal, p.valor_total) as valor_subtotal,
                        COALESCE(p.desconto, 0.0) as desconto,
                        COALESCE(p.frete, 0.0) as frete,
                        CAST(p.valor_total AS FLOAT) as valor_total,
                        p.endereco_entrega,
                        COALESCE(p.responsavel, 'Vendedor') as responsavel,
                        p.observacoes
                    FROM pedidos p
                    LEFT JOIN clientes c ON p.cliente_id = c.id
                    WHERE p.id = %s;
                """, (id,))
                linha = cursor.fetchone()
                if not linha:
                    return None

                pedido = self._mapear_linha(linha)

                cursor.execute("""
                    SELECT 
                        i.id,
                        i.produto_id,
                        p.nome AS produto_nome,
                        i.quantidade,
                        CAST(i.preco_unitario AS FLOAT) AS preco_unitario,
                        CAST(i.subtotal AS FLOAT) AS subtotal
                    FROM itens_pedido i
                    JOIN produtos p ON i.produto_id = p.id
                    WHERE i.pedido_id = %s;
                """, (id,))
                itens_linhas = cursor.fetchall()
                for item_l in itens_linhas:
                    item = ItemPedido(
                        id=item_l['id'],
                        produto_id=item_l['produto_id'],
                        produto_nome=item_l['produto_nome'],
                        quantidade=item_l['quantidade'],
                        preco_unitario=item_l['preco_unitario']
                    )
                    pedido.adicionar_item(item)

                return pedido
        finally:
            if should_close:
                conn.close()

    def salvar_transacional(self, pedido: Pedido, conn) -> int:
        """Salva o pedido completo e seus itens dentro de uma transação aberta."""
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO pedidos 
                (numero_pedido, cliente_id, data_pedido, data_prevista_entrega, status, status_pagamento, 
                 forma_pagamento, valor_subtotal, desconto, frete, valor_total, endereco_entrega, responsavel, observacoes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    pedido.numero_pedido,
                    pedido.cliente_id,
                    pedido.data_pedido,
                    pedido.data_prevista_entrega,
                    pedido.status,
                    pedido.status_pagamento,
                    pedido.forma_pagamento,
                    pedido.valor_subtotal,
                    pedido.desconto,
                    pedido.frete,
                    pedido.valor_total,
                    pedido.endereco_entrega,
                    pedido.responsavel,
                    pedido.observacoes
                )
            )
            pedido_id = cursor.lastrowid

            # Gera numero_pedido se ainda não setado
            if not pedido.numero_pedido:
                num = f"PED-{pedido_id:04d}"
                cursor.execute("UPDATE pedidos SET numero_pedido = %s WHERE id = %s;", (num, pedido_id))

            for item in pedido.itens:
                cursor.execute(
                    """
                    INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (pedido_id, item.produto_id, item.quantidade, item.preco_unitario, item.subtotal)
                )

            return pedido_id

    def atualizar_status(self, id: int, novo_status: str, conn=None) -> bool:
        """Atualiza o status operacional do pedido."""
        conexao = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with conexao.cursor() as cursor:
                cursor.execute("UPDATE pedidos SET status = %s WHERE id = %s;", (novo_status, id))
                if cursor.rowcount == 0:
                    cursor.execute("SELECT id FROM pedidos WHERE id = %s;", (id,))
                    if not cursor.fetchone():
                        return False
                if conn is None:
                    conexao.commit()
                return True
        except Exception:
            if conn is None: conexao.rollback()
            raise
        finally:
            if should_close: conexao.close()

    def atualizar_status_pagamento(self, id: int, novo_status_pagamento: str, conn=None) -> bool:
        """Atualiza o status financeiro de pagamento do pedido."""
        conexao = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with conexao.cursor() as cursor:
                cursor.execute("UPDATE pedidos SET status_pagamento = %s WHERE id = %s;", (novo_status_pagamento, id))
                if conn is None: conexao.commit()
                return True
        except Exception:
            if conn is None: conexao.rollback()
            raise
        finally:
            if should_close: conexao.close()

    def registrar_historico(self, pedido_id: int, status_anterior: str, status_novo: str,
                            responsavel: str, tipo_alteracao: str = "Status Pedido", observacao: str = "", conn=None):
        """Grava log de auditoria cronológico para o pedido."""
        conexao = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO historico_pedidos (pedido_id, status_anterior, status_novo, tipo_alteracao, observacao, responsavel)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (pedido_id, status_anterior, status_novo, tipo_alteracao, observacao, responsavel)
                )
                if conn is None: conexao.commit()
        except Exception:
            if conn is None: conexao.rollback()
            raise
        finally:
            if should_close: conexao.close()

    def listar_historico(self, pedido_id: int) -> list:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, pedido_id, status_anterior, status_novo, tipo_alteracao, observacao, responsavel, data_registro
                    FROM historico_pedidos
                    WHERE pedido_id = %s
                    ORDER BY id DESC;
                    """,
                    (pedido_id,)
                )
                linhas = cursor.fetchall() or []
                for item in linhas:
                    if 'data_registro' in item:
                        item['data_registro_formatada'] = formatar_data_br(item['data_registro'], incluir_hora=True)
                        item['data_registro'] = item['data_registro_formatada']
                return linhas
        finally:
            if should_close: conn.close()

    def registrar_cancelamento_devolucao(self, pedido_id: int, tipo: str, motivo: str, solicitante: str,
                                         status_aprovacao: str = "Aprovado", aprovador: str = None, conn=None) -> int:
        conexao = conn or self._get_connection()
        should_close = conn is None and self._connection is None
        try:
            with conexao.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO cancelamentos_devolucoes 
                    (pedido_id, tipo, motivo, solicitante, status_aprovacao, aprovador, data_aprovacao)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW());
                    """,
                    (pedido_id, tipo, motivo, solicitante, status_aprovacao, aprovador or solicitante)
                )
                cid = cursor.lastrowid
                if conn is None: conexao.commit()
                return cid
        except Exception:
            if conn is None: conexao.rollback()
            raise
        finally:
            if should_close: conexao.close()

    def listar_cancelamentos_devolucoes(self, pedido_id: int = None) -> list:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                query = "SELECT * FROM cancelamentos_devolucoes"
                params = []
                if pedido_id:
                    query += " WHERE pedido_id = %s"
                    params.append(pedido_id)
                query += " ORDER BY id DESC;"
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
        finally:
            if should_close: conn.close()

    def obter_indicadores_operacionais(self) -> dict:
        """Calcula os indicadores operacionais clicáveis exigidos."""
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN status = 'Aguardando Pagamento' THEN 1 ELSE 0 END) as aguardando_pagamento,
                        SUM(CASE WHEN status = 'Aguardando Separação' THEN 1 ELSE 0 END) as aguardando_separacao,
                        SUM(CASE WHEN status = 'Em Separação' THEN 1 ELSE 0 END) as em_separacao,
                        SUM(CASE WHEN status = 'Pronto para Envio' THEN 1 ELSE 0 END) as prontos_para_envio,
                        SUM(CASE WHEN data_prevista_entrega IS NOT NULL AND data_prevista_entrega < CURDATE() AND status NOT IN ('Entregue', 'Cancelado', 'Devolvido', 'Recusado') THEN 1 ELSE 0 END) as atrasados,
                        COUNT(id) as total_geral
                    FROM pedidos;
                """)
                l = cursor.fetchone() or {}
                return {
                    "aguardando_pagamento": int(l.get('aguardando_pagamento') or 0),
                    "aguardando_separacao": int(l.get('aguardando_separacao') or 0),
                    "em_separacao": int(l.get('em_separacao') or 0),
                    "prontos_para_envio": int(l.get('prontos_para_envio') or 0),
                    "atrasados": int(l.get('atrasados') or 0),
                    "total_geral": int(l.get('total_geral') or 0)
                }
        finally:
            if should_close: conn.close()

    def contar_total(self) -> int:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total_pedidos FROM pedidos;")
                linha = cursor.fetchone()
                return int(linha.get('total_pedidos') or 0)
        finally:
            if should_close: conn.close()

    def somar_vendas_totais(self) -> float:
        """Calcula faturamento total excluindo pedidos cancelados ou recusados."""
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COALESCE(SUM(valor_total), 0.00) AS total_vendas FROM pedidos WHERE status NOT IN ('Cancelado', 'Recusado');")
                return float(cursor.fetchone()['total_vendas'])
        finally:
            if should_close: conn.close()
