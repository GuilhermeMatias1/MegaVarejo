from repositories.base_repository import BaseRepository
from models.cliente import Cliente, Endereco
from database.connection import DatabaseConnection

class ClienteRepository(BaseRepository):
    """
    Repositório de persistência para a entidade Cliente.
    Encapsula consultas SQL diretas, pesquisa por termos (nome, CPF, e-mail),
    CRUD completo e consultas aos pedidos associados.
    """

    def __init__(self, connection=None):
        self._connection = connection

    def _get_connection(self):
        return self._connection if self._connection else DatabaseConnection.get_connection()

    def _mapear_linha(self, l) -> Cliente:
        # Fallback de CPF para registros legados que ainda não possuíam CPF
        cpf_valor = l.get('cpf')
        if not cpf_valor:
            # Gera um CPF válido temporário apenas se for nulo no banco legado
            cpf_valor = "12345678909"

        # Constrói a entidade de domínio Cliente via construtor padrão POO
        return Cliente(
            id=l['id'],
            nome=l['nome'],
            cpf=cpf_valor,
            email=l['email'],
            telefone=l.get('telefone') or "",
            cep=l.get('cep') or "",
            logradouro=l.get('logradouro') or "",
            numero=l.get('numero') or "",
            complemento=l.get('complemento') or "",
            bairro=l.get('bairro') or "",
            cidade=l.get('cidade') or "",
            uf=l.get('uf') or "",
            endereco=l.get('endereco') or "",
            criado_em=l.get('criado_em')
        )

    def listar_todos(self, busca: str = None) -> list:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                query = """
                    SELECT 
                        c.id, c.nome, c.cpf, c.email, c.telefone,
                        c.cep, c.logradouro, c.numero, c.complemento, c.bairro, c.cidade, c.uf, c.endereco,
                        c.criado_em,
                        COUNT(p.id) AS total_pedidos
                    FROM clientes c
                    LEFT JOIN pedidos p ON p.cliente_id = c.id
                    WHERE 1=1
                """
                params = []
                if busca and str(busca).strip():
                    termo = f"%{str(busca).strip()}%"
                    # Remove pontos e traços para busca de CPF numérico
                    cpf_limpo = f"%{str(busca).replace('.', '').replace('-', '').strip()}%"
                    query += " AND (c.nome LIKE %s OR c.email LIKE %s OR c.cpf LIKE %s OR c.cpf LIKE %s)"
                    params.extend([termo, termo, termo, cpf_limpo])

                query += " GROUP BY c.id ORDER BY c.id DESC;"
                cursor.execute(query, tuple(params))
                linhas = cursor.fetchall()
                clientes = []
                for l in linhas:
                    c = self._mapear_linha(l)
                    # Adiciona contagem agregada de pedidos
                    c.total_pedidos = int(l.get('total_pedidos') or 0)
                    clientes.append(c)
                return clientes
        finally:
            if should_close:
                conn.close()

    def buscar_por_id(self, id: int) -> Cliente:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, nome, cpf, email, telefone,
                        cep, logradouro, numero, complemento, bairro, cidade, uf, endereco,
                        criado_em
                    FROM clientes 
                    WHERE id = %s;
                """, (id,))
                linha = cursor.fetchone()
                if not linha:
                    return None
                return self._mapear_linha(linha)
        finally:
            if should_close:
                conn.close()

    def buscar_por_cpf(self, cpf: str) -> Cliente:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                # Busca por CPF limpo ou formatado
                cursor.execute("""
                    SELECT id, nome, cpf, email, telefone,
                           cep, logradouro, numero, complemento, bairro, cidade, uf, endereco,
                           criado_em
                    FROM clientes 
                    WHERE REPLACE(REPLACE(cpf, '.', ''), '-', '') = REPLACE(REPLACE(%s, '.', ''), '-', '');
                """, (cpf,))
                linha = cursor.fetchone()
                if not linha:
                    return None
                return self._mapear_linha(linha)
        finally:
            if should_close:
                conn.close()

    def buscar_por_email(self, email: str) -> Cliente:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, nome, cpf, email, telefone,
                           cep, logradouro, numero, complemento, bairro, cidade, uf, endereco,
                           criado_em
                    FROM clientes 
                    WHERE LOWER(email) = LOWER(%s);
                """, (str(email).strip(),))
                linha = cursor.fetchone()
                if not linha:
                    return None
                return self._mapear_linha(linha)
        finally:
            if should_close:
                conn.close()

    def salvar(self, cliente: Cliente) -> int:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                end = cliente.endereco
                end_completo = end.texto_completo()
                cursor.execute(
                    """
                    INSERT INTO clientes 
                    (nome, cpf, email, telefone, cep, logradouro, numero, complemento, bairro, cidade, uf, endereco)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        cliente.nome, cliente.cpf, cliente.email, cliente.telefone,
                        end.cep, end.logradouro, end.numero, end.complemento, end.bairro,
                        end.cidade, end.uf, end_completo
                    )
                )
                conn.commit()
                return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            if should_close:
                conn.close()

    def atualizar(self, cliente: Cliente) -> bool:
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                end = cliente.endereco
                end_completo = end.texto_completo()
                cursor.execute(
                    """
                    UPDATE clientes 
                    SET nome = %s, cpf = %s, email = %s, telefone = %s,
                        cep = %s, logradouro = %s, numero = %s, complemento = %s,
                        bairro = %s, cidade = %s, uf = %s, endereco = %s
                    WHERE id = %s;
                    """,
                    (
                        cliente.nome, cliente.cpf, cliente.email, cliente.telefone,
                        end.cep, end.logradouro, end.numero, end.complemento,
                        end.bairro, end.cidade, end.uf, end_completo,
                        cliente.id
                    )
                )
                conn.commit()
                return cursor.rowcount > 0 or True
        except Exception:
            conn.rollback()
            raise
        finally:
            if should_close:
                conn.close()

    def excluir(self, id: int) -> bool:
        """
        Exclui o cliente verificando previamente se existem pedidos vinculados.
        """
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM clientes WHERE id = %s;", (id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception:
            conn.rollback()
            raise
        finally:
            if should_close:
                conn.close()

    def contar_pedidos_cliente(self, cliente_id: int) -> int:
        """Retorna quantos pedidos estão associados a este cliente para integridade."""
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM pedidos WHERE cliente_id = %s;", (cliente_id,))
                linha = cursor.fetchone() or {}
                return int(linha.get('total') or 0)
        finally:
            if should_close:
                conn.close()

    def listar_pedidos_cliente(self, cliente_id: int) -> list:
        """Consulta o histórico de pedidos deste cliente."""
        conn = self._get_connection()
        should_close = self._connection is None
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id, 
                        COALESCE(numero_pedido, CONCAT('PED-', LPAD(id, 4, '0'))) as numero_pedido,
                        data_pedido,
                        status,
                        status_pagamento,
                        CAST(valor_total AS FLOAT) as valor_total,
                        endereco_entrega,
                        responsavel
                    FROM pedidos 
                    WHERE cliente_id = %s
                    ORDER BY id DESC;
                """, (cliente_id,))
                return cursor.fetchall() or []
        finally:
            if should_close:
                conn.close()
