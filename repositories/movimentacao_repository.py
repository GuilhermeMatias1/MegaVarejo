from repositories.base_repository import BaseRepository
from models.movimentacao_estoque import MovimentacaoEstoque
from database.connection import DatabaseConnection

class MovimentacaoRepository(BaseRepository):
    """
    Repositório de persistência para as movimentações de estoque (Auditoria / Kardex).
    """

    def __init__(self, connection=None):
        self._connection = connection

    def _get_connection(self):
        return self._connection if self._connection else DatabaseConnection.get_connection()

    def _mapear_linha(self, l) -> MovimentacaoEstoque:
        return MovimentacaoEstoque(
            id=l['id'],
            produto_id=l['produto_id'],
            produto_nome=l.get('produto_nome', ''),
            tipo=l['tipo'],
            quantidade=l['quantidade'],
            saldo_anterior=l['saldo_anterior'],
            novo_saldo=l['novo_saldo'],
            motivo=l['motivo'],
            responsavel=l['responsavel'],
            data_movimentacao=l['data_movimentacao']
        )

    def listar_todos(self, limite: int = 100, produto_id: int = None, tipo: str = None) -> list:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                query = """
                    SELECT 
                        m.id, 
                        m.produto_id, 
                        p.nome as produto_nome,
                        m.tipo, 
                        m.quantidade, 
                        m.saldo_anterior, 
                        m.novo_saldo, 
                        m.motivo, 
                        m.responsavel, 
                        m.data_movimentacao
                    FROM movimentacoes_estoque m
                    JOIN produtos p ON m.produto_id = p.id
                    WHERE 1=1
                """
                params = []
                if produto_id:
                    query += " AND m.produto_id = %s"
                    params.append(int(produto_id))
                if tipo:
                    query += " AND m.tipo = %s"
                    params.append(str(tipo))

                query += " ORDER BY m.id DESC LIMIT %s;"
                params.append(int(limite))

                cursor.execute(query, tuple(params))
                linhas = cursor.fetchall()
                return [self._mapear_linha(l) for l in linhas]
        finally:
            if should_close:
                conn.close()

    def buscar_por_id(self, id: int) -> MovimentacaoEstoque:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        m.id, 
                        m.produto_id, 
                        p.nome as produto_nome,
                        m.tipo, 
                        m.quantidade, 
                        m.saldo_anterior, 
                        m.novo_saldo, 
                        m.motivo, 
                        m.responsavel, 
                        m.data_movimentacao
                    FROM movimentacoes_estoque m
                    JOIN produtos p ON m.produto_id = p.id
                    WHERE m.id = %s;
                """, (id,))
                linha = cursor.fetchone()
                if not linha:
                    return None
                return self._mapear_linha(linha)
        finally:
            if should_close:
                conn.close()

    def salvar_transacional(self, mov: MovimentacaoEstoque, conn) -> int:
        """Persiste um registro de movimentação dentro de uma transação aberta."""
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO movimentacoes_estoque 
                (produto_id, tipo, quantidade, saldo_anterior, novo_saldo, motivo, responsavel, data_movimentacao)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    mov.produto_id,
                    mov.tipo,
                    mov.quantidade,
                    mov.saldo_anterior,
                    mov.novo_saldo,
                    mov.motivo,
                    mov.responsavel,
                    mov.data_movimentacao
                )
            )
            return cursor.lastrowid

    def relatorio_produtos_mais_movimentados(self, limite: int = 5) -> list:
        """Gera relatório de produtos com maior frequência de movimentação."""
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        p.id, 
                        COALESCE(p.codigo, CONCAT('PRD-', LPAD(p.id, 3, '0'))) as codigo,
                        p.nome, 
                        COUNT(m.id) as total_movimentacoes,
                        COALESCE(SUM(m.quantidade), 0) as total_unidades_movimentadas
                    FROM produtos p
                    JOIN movimentacoes_estoque m ON p.id = m.produto_id
                    GROUP BY p.id, p.codigo, p.nome
                    ORDER BY total_movimentacoes DESC, total_unidades_movimentadas DESC
                    LIMIT %s;
                """, (limite,))
                return cursor.fetchall()
        finally:
            if should_close:
                conn.close()
